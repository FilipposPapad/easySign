import sys
from pathlib import Path
import uuid
import asyncio
from core.providers.websign import ApiClient

from pyhanko.sign import fields, signers
from pyhanko import stamp
from pyhanko.sign.signers import PdfSigner, PdfSignatureMetadata
from pyhanko.sign.timestamps import HTTPTimeStamper
from pyhanko_certvalidator import ValidationContext
from pyhanko.sign.general import load_cert_from_pemder
from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
from pyhanko.pdf_utils.reader import PdfFileReader
from pyhanko.pdf_utils import generic


# ===============================
# Remote Signer Class
# ===============================
class RemoteSigner(signers.ExternalSigner):

    def __init__(self, api_client, sign_password, signing_cert, cert_chain):
        super().__init__(signing_cert=signing_cert, cert_registry=cert_chain)
        self.api_client = api_client
        self.sign_password = sign_password

    async def async_sign_raw(
        self, data: bytes, digest_algorithm: str, dry_run=False
    ) -> bytes:

        if dry_run:
            return b"\x00" * 256  # dummy length for CMS size estimation

        signature = self.api_client.sign([data], self.sign_password)
        return signature[0]


# ===============================
#  BatchSigner Class
#   waits until the signature is ready from a batch api call
# ===============================


class BatchSigner(signers.ExternalSigner):

    def __init__(self, signing_cert, cert_chain):
        super().__init__(signing_cert=signing_cert, cert_registry=cert_chain)
        self.data_to_sign: bytes | None = None
        self._sig_ready = asyncio.Event()
        self._data_ready = asyncio.Event()
        self.prefetched_sig: bytes | None = None

    async def async_sign_raw(
        self, data: bytes, digest_algorithm: str, dry_run=False
    ) -> bytes:
        if dry_run:
            return b"\x00" * 8192

        self.data_to_sign = data
        self._data_ready.set()

        await self._sig_ready.wait()
        return self.prefetched_sig

    def provide_signature(self, sig: bytes):
        self.prefetched_sig = sig
        self._sig_ready.set()


class Signer:

    def __init__(self, base_url, tsa_url, tss_cert_file, username, password):
        self.api_client = ApiClient(
            base_url,
            username,
            password,
        )

        self.cert_chain = self.api_client.get_certificates()

        self.tsa_url = tsa_url

        self.tss_cert = load_cert_from_pemder(tss_cert_file)

        self.unique_id = str(uuid.uuid4())[:8]

    def sign_pdf(
        self, input_pdf, stamp_position, sign_password, deny_active_content=True
    ):

        if deny_active_content and self.scan_pdf_for_active_content(input_pdf):
            return (None, input_pdf)

        signing_cert = self.cert_chain[0]
        intermediates = self.cert_chain[1:]
        root_cert = self.cert_chain[-1]

        remote_signer = RemoteSigner(
            self.api_client, sign_password, signing_cert, self.cert_chain
        )

        tsa = HTTPTimeStamper(self.tsa_url)

        vc = ValidationContext(
            trust_roots=[root_cert, self.tss_cert],
            other_certs=intermediates,
            allow_fetching=True,
            revocation_mode="hard-fail",
        )

        meta = PdfSignatureMetadata(
            field_name=f"Sig_{self.unique_id}",
            md_algorithm="sha256",
            validation_context=vc,
            embed_validation_info=True,
            use_pades_lta=True,
        )

        stamp_style = stamp.TextStampStyle(
            stamp_text=("%(signer)s\n" "%(ts)s"),
            timestamp_format="%d/%m/%Y %H:%M",
            border_width=0,
            background=None,
        )

        pdf_signer = PdfSigner(
            meta, signer=remote_signer, timestamper=tsa, stamp_style=stamp_style
        )

        input_path = Path(input_pdf)
        output_file = str(input_path.with_name(f"{input_path.stem}_signed.pdf"))

        with open(input_pdf, "rb") as inf:
            writer = IncrementalPdfFileWriter(inf, strict=False)

            stamp_box = self._calc_stamp_box(writer, stamp_position)

            fields.append_signature_field(
                writer,
                sig_field_spec=fields.SigFieldSpec(
                    f"Sig_{self.unique_id}", box=stamp_box, on_page=0
                ),
            )

            writer.hybrid_xrefs = True

            with open(output_file, "wb") as outf:
                pdf_signer.sign_pdf(writer, output=outf, in_place=False)

        return (output_file, input_pdf)

    async def sign_all_pdfs(
        self,
        documents: list,
        stamp_position: int,
        sign_password: str,
        deny_active_content=True,
    ):

        rejected = [
            d
            for d in documents
            if deny_active_content and self.scan_pdf_for_active_content(d)
        ]
        approved = [d for d in documents if d not in rejected]

        signers_list = []
        tasks = []

        for input_pdf in approved:
            batch_signer = BatchSigner(self.cert_chain[0], self.cert_chain)
            signers_list.append(batch_signer)
            task = asyncio.create_task(
                self._run_pipeline(input_pdf, stamp_position, batch_signer)
            )
            tasks.append(task)

        await asyncio.gather(*[s._data_ready.wait() for s in signers_list])

        all_data = [s.data_to_sign for s in signers_list]
        signatures = self.api_client.sign(all_data, sign_password)

        for s, sig in zip(signers_list, signatures):
            s.provide_signature(sig)

        results = await asyncio.gather(*tasks)

        rejected = [(None, r) for r in rejected]

        return results + rejected

    async def _run_pipeline(
        self, input_pdf: str, stamp_position: int, batch_signer: BatchSigner
    ) -> tuple:

        tsa = HTTPTimeStamper(self.tsa_url)

        vc = ValidationContext(
            trust_roots=[self.cert_chain[-1], self.tss_cert],
            other_certs=self.cert_chain[1:],
            allow_fetching=True,
            revocation_mode="hard-fail",
        )

        meta = PdfSignatureMetadata(
            field_name=f"Sig_{self.unique_id}",
            md_algorithm="sha256",
            validation_context=vc,
            embed_validation_info=True,
            use_pades_lta=True,
        )

        stamp_style = stamp.TextStampStyle(
            stamp_text="%(signer)s\n%(ts)s",
            timestamp_format="%d/%m/%Y %H:%M",
            border_width=0,
            background=None,
        )

        pdf_signer = PdfSigner(
            meta, signer=batch_signer, timestamper=tsa, stamp_style=stamp_style
        )

        input_path = Path(input_pdf)
        output_file = str(input_path.with_name(f"{input_path.stem}_signed.pdf"))

        with open(input_pdf, "rb") as inf:
            writer = IncrementalPdfFileWriter(inf, strict=False)

            stamp_box = self._calc_stamp_box(writer, stamp_position)

            fields.append_signature_field(
                writer,
                sig_field_spec=fields.SigFieldSpec(
                    f"Sig_{self.unique_id}", box=stamp_box, on_page=0
                ),
            )
            writer.hybrid_xrefs = True

            with open(output_file, "wb") as outf:
                await pdf_signer.async_sign_pdf(writer, output=outf, in_place=False)

        return (output_file, input_pdf)

    def _calc_stamp_box(self, writer, stamp_position: int) -> tuple:
        page = writer.root["/Pages"]["/Kids"][0].get_object()
        media_box = page["/MediaBox"]
        page_width = float(media_box[2])
        page_height = float(media_box[3])

        box_width, box_height = 150, 40
        marginX, marginY = 30, 20

        x1 = (
            marginX
            if stamp_position in (1, 4)
            else (
                ((page_width - box_width) / 2)
                if stamp_position in (2, 5)
                else page_width - box_width - marginX
            )
        )
        x2 = (
            marginX + box_width
            if stamp_position in (1, 4)
            else (
                ((page_width + box_width) / 2)
                if stamp_position in (2, 5)
                else page_width - marginX
            )
        )

        y1 = (
            marginY
            if stamp_position in (4, 5, 6)
            else page_height - box_height - marginY
        )
        y2 = (
            marginY + box_height
            if stamp_position in (4, 5, 6)
            else page_height - marginY
        )

        return (x1, y1, x2, y2)

    def scan_pdf_for_active_content(self, pdf_path: str) -> bool:

        def resolve(obj):
            if isinstance(obj, generic.IndirectObject):
                return obj.get_object()
            return obj

        def action_is_dangerous(action):

            action = resolve(action)

            if not isinstance(action, generic.DictionaryObject):
                return False

            action_type = action.get("/S")

            if action_type in [
                generic.NameObject("/JavaScript"),
                generic.NameObject("/Launch"),
                generic.NameObject("/SubmitForm"),
                generic.NameObject("/ImportData"),
            ]:
                return True

            return False

        def walk_pages(node):

            node = resolve(node)

            if node.get("/Type") == generic.NameObject("/Page"):
                yield node
                return

            if "/Kids" in node:
                for kid in node["/Kids"]:
                    yield from walk_pages(kid)

        with open(pdf_path, "rb") as f:

            reader = PdfFileReader(f)
            root = resolve(reader.root)

            # --------------------------------------------------
            # Names dictionary
            # --------------------------------------------------

            names = root.get("/Names")
            names = resolve(names)

            if names:

                if "/JavaScript" in names:
                    return True

                if "/EmbeddedFiles" in names:
                    return True

            # --------------------------------------------------
            # OpenAction
            # --------------------------------------------------

            open_action = root.get("/OpenAction")

            if action_is_dangerous(open_action):
                return True

            # --------------------------------------------------
            # AcroForm
            # --------------------------------------------------

            acro = root.get("/AcroForm")
            acro = resolve(acro)

            if acro:

                fields = acro.get("/Fields", [])

                for field in fields:

                    field = resolve(field)

                    for key in ["/A", "/AA"]:

                        action = field.get(key)

                        if action_is_dangerous(action):
                            return True

            # --------------------------------------------------
            # Pages
            # --------------------------------------------------

            pages = root["/Pages"]

            for page in walk_pages(pages):

                # Page additional actions
                aa = page.get("/AA")

                if isinstance(aa, generic.DictionaryObject):

                    for action in aa.values():

                        if action_is_dangerous(action):
                            return True

                # Annotations
                annots = page.get("/Annots")

                if annots:

                    for annot in annots:

                        annot = resolve(annot)

                        action = annot.get("/A")

                        if action_is_dangerous(action):
                            return True

                        aa = annot.get("/AA")

                        if isinstance(aa, generic.DictionaryObject):

                            for action in aa.values():

                                if action_is_dangerous(action):
                                    return True

                # RichMedia (embedded flash/video)
                if "/RichMedia" in page:
                    return True

        return False
