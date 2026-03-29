import os
from pathlib import Path
import webbrowser
import tkinter as tk
from tkinter import messagebox
from tkinter import ttk

from core.converter import is_doc_file, convert_doc_to_pdf, convert_folder_docs_to_pdfs
from utils.helpers import (
    get_documents_from_folder,
    get_base_path,
    save_password,
    load_password,
    load_config,
)

from core.providers.websign import ApiClient
from core.signer import Signer
from core.executor import Executor


SERVICE_NAME = "easySignApp"


class SignApp:
    def __init__(self, root, file_path):
        self.root = root
        self.file_path = file_path
        self.is_folder = Path(file_path).is_dir()
        self.cleanup = False
        self.data_to_sign = None

        self.executor = Executor(self.root)

        self.base_path = get_base_path()

        try:
            self.config = load_config()

            self.api_base_url = self.config["api"]["base_url"]
            self.tsa_url = self.config["api"]["tsa_url"]
            self.tss_cert_file = self.config["security"]["tss_cert_file"]

            self.window_width = self.config.get("window", {}).get("width", 420)
            self.window_height = self.config.get("window", {}).get("height", 350)
            self.window_bgcolor = self.config.get("window", {}).get(
                "bgcolor", "lightblue"
            )

        except AssertionError as e:
            self.show_error("Προσοχή: Το αρχείο ρυθμίσεων δεν είναι έγκυρο:" + str(e))
            root.destroy()

        self.setup_window()
        self.create_widgets()

    def setup_window(self):
        title_suffix = "Εγγράφων" if self.is_folder else "Εγγράφου"
        self.root.title(f"easySign - Ψηφιακή Υπογραφή {title_suffix}")

        self.root.geometry(f"{self.window_width}x{self.window_height}")

        self.root.resizable(False, False)

        self.root.configure(bg=self.window_bgcolor)

        self.root.iconbitmap(
            str(self.base_path / "resources" / "images" / "signclient.ico")
        )

    def create_widgets(self):
        label_text = "Φάκελος : " if self.is_folder else "Αρχείο : "
        display_path = (
            self.file_path if len(self.file_path) < 50 else "..." + self.file_path[-45:]
        )

        ttk.Label(self.root, text=label_text + display_path).grid(
            row=0, columnspan=2, column=0, pady=5, padx=10
        )

        self.convert_img = tk.PhotoImage(
            file=str(self.base_path / "resources" / "images" / "pdf.png")
        )
        self.sign_img = tk.PhotoImage(
            file=str(self.base_path / "resources" / "images" / "signature.png")
        )
        self.request_otp_img = tk.PhotoImage(
            file=str(self.base_path / "resources" / "images" / "get.png")
        )

        if self.is_folder:
            self.convert_imgbtn = ttk.Label(
                self.root, image=self.convert_img, cursor="hand2"
            )
            self.convert_imgbtn.grid(row=0, column=2, pady=5, ipadx=5, sticky="w")
            self.convert_imgbtn.bind("<Button-1>", self.convert_folder_docs)

        self.separator = ttk.Separator(self.root, orient=tk.HORIZONTAL)
        self.separator.grid(
            row=1,
            column=0,
            columnspan=3,
            sticky="ew",
            pady=5,
            padx=10,
        )

        ttk.Label(self.root, text="Όνομα Χρήστη: ").grid(
            row=2, column=0, pady=10, sticky="e"
        )
        self.entry_user = ttk.Entry(self.root)
        self.entry_user.grid(row=2, column=1, sticky="w")

        self.entry_user.bind("<FocusOut>", self.autofill_password)

        ttk.Label(self.root, text="Κωδικός: ").grid(
            row=3, column=0, pady=10, sticky="e"
        )
        self.entry_pass = ttk.Entry(self.root, show="*")
        self.entry_pass.grid(row=3, column=1, sticky="w")

        ttk.Label(self.root, text="OTP: ").grid(row=4, column=0, pady=10, sticky="e")
        self.entry_otp = ttk.Entry(self.root)
        self.entry_otp.grid(row=4, column=1, sticky="w")
        self.entry_otp.bind("<Return>", lambda event: self.btn_sign.invoke())

        self.request_otp_imgbtn = ttk.Label(
            self.root, image=self.request_otp_img, cursor="hand2"
        )
        self.request_otp_imgbtn.grid(row=4, column=2, pady=10, ipadx=5, sticky="w")
        self.request_otp_imgbtn.bind("<Button-1>", self.request_otp_from_api)

        ttk.Label(self.root, text="Θέση Στάμπας: ").grid(
            row=5, column=0, pady=10, sticky="e"
        )
        stamp_positions = [
            "Πάνω Αριστερά",
            "Πάνω Κέντρο",
            "Πάνω Δεξιά",
            "Κάτω Αριστερά",
            "Κάτω Κέντρο",
            "Κάτω Δεξιά",
        ]
        self.positionCombo = ttk.Combobox(
            self.root, values=stamp_positions, state="readonly", takefocus=False
        )
        self.positionCombo.set("Πάνω Δεξιά")
        self.positionCombo.grid(row=5, column=1, sticky="w")

        # Κουμπί υπογραφής
        self.btn_sign = ttk.Button(
            self.root,
            image=self.sign_img,
            text=(
                "Βάλε ψηφιακή υπογραφή σε όλα τα PDF αρχεία"
                if self.is_folder
                else "Βάλε ψηφιακή υπογραφή στο αρχείο"
            ),
            compound="left",
            command=self.sign_clicked,
        )
        self.btn_sign.grid(
            row=6, column=0, columnspan=3, ipady=1, pady=15, padx=20, sticky="ew"
        )

        self.progress = ttk.Progressbar(self.root, mode="indeterminate")
        self.progress.grid(
            row=7,
            column=0,
            columnspan=3,
            pady=1,
            padx=20,
            sticky="ew",
        )

        self.copyright = ttk.Label(
            self.root, text="\u00a9Φίλιππος Παπαδακάκης", cursor="hand2"
        )
        self.copyright.grid(row=8, column=0, columnspan=3, pady=10, padx=10, sticky="e")
        self.copyright.bind(
            "<Button-1>",
            lambda e: webbrowser.open_new("https://github.com/FilipposPapad/easySign"),
        )

        style = ttk.Style()
        style.theme_use("alt")
        style.configure(
            "TButton",
            background="#0C2762",
            foreground="#B7DEF7",
            width=55,
            borderwidth=1,
            focusthickness=3,
            focuscolor="#1E6ECA",
        )
        style.configure("TLabel", background=self.window_bgcolor, foreground="#042062")
        style.map("TButton", background=[("active", "#1E6ECA")])

        self.entry_user.focus()

    # ---------------- Sign Clicked Event----------------

    def sign_clicked(self):

        if self.is_folder:
            file_list = get_documents_from_folder(self.file_path, {".pdf"})
        else:
            if is_doc_file(self.file_path):
                self.cleanup = True
                self.convert_doc(self.file_path)
                return
            else:
                self.cleanup = False
                file_list = [self.file_path]

        self.btn_sign.config(state="disabled")

        self.progress.start()

        self.executor.submit(self.sign_files, self.sign_files_result, file_list)

    # ---------------- Signing ----------------

    def sign_files(self, file_list):
        username = self.get_username()
        password = self.get_password()
        otp = self.get_otp()
        position = self.positionCombo.current() + 1

        if not username or not password:
            self.show_error("Παρακαλώ συμπληρώστε όλα τα πεδία.")
            return

        self.progress.start()

        signer = Signer(
            self.api_base_url, self.tsa_url, self.tss_cert_file, username, password
        )

        number_of_files = len(file_list)

        if number_of_files == 1:
            sign_result = signer.sign_pdf(file_list[0], position, otp)
            sign_results = [sign_result]
        else:
            sign_results = signer.sign_all_pdfs(file_list, position, otp)

        return sign_results

    def sign_files_result(self, status, results):

        self.stop_progress()

        if status == "success":
            username = self.get_username()
            password = self.get_password()
            saved_password = load_password(SERVICE_NAME, username)

            if saved_password:
                if saved_password != password:
                    save_password(SERVICE_NAME, username, password)
            else:
                confirm = messagebox.askyesno(
                    title="Επιβεβαίωση",
                    message="Θέλετε να αποθηκευσετε τα διεπιστευτήρια (Όνομα Χρήστη - Κωδικο) σε αυτόν τον υπολογιστή;",
                )
                if confirm:
                    save_password(SERVICE_NAME, username, password)

            number_of_documents = len(results)

            if number_of_documents == 1:
                result = results[0]

                if self.cleanup and os.path.exists(result[1]):
                    os.remove(result[1])

                if result[0] is not None:
                    self.show_info("Το έγγραφο υπογράφηκε επιτυχώς!")
                    os.startfile(result[0])
                else:
                    self.show_error(
                        "Η Υπογραφή του εγγραφου απέτυχε λόγω ύπαρξης ενεργού περιεχομένου."
                    )
            else:
                succes = [d[1] for d in results if d[0] is not None]
                fail = [d[1] for d in results if d[0] is None]

                msg = f"Υπογράφησαν επιτυχώς {len(succes)} έγγραφα:\n" + "\n".join(
                    succes
                )

                if fail:
                    msg += (
                        f"\n\nΑπέτυχε η υπογραφή {len(fail)} εγγράφων λόγω ύπαρξης ενεργού περιεχομένου:\n"
                        + "\n".join(fail)
                    )

                self.show_info(msg)

            self.root.destroy()

        elif status == "error":
            self.show_error(results)

    # ---------------- OTP ----------------

    def request_otp_from_api(self, event=None):

        username = self.get_username()
        password = self.get_password()

        if not username or not password:
            self.show_error("Παρακαλώ συμπληρώστε πρώτα το Όνομα Χρήστη και τον Κωδικό.")
            return

        confirm = messagebox.askyesno(
            title="Επιβεβαίωση",
            message="Εάν έχετε ενεργοποιήσει την αποστολή OTP με email θα πραγματοποιηθεί η αποστολή.\n\nΘέλετε να συνεχίσετε;",
        )

        if not confirm:
            return

        api = ApiClient(self.api_base_url, username, password)

        self.progress.start()
        self.executor.submit(api.request_otp, self.request_otp_result)

    def request_otp_result(self, status, result):

        self.stop_progress()

        if status == "success":
            self.show_info(result)
        else:
            self.show_error(result)

    # ---------------- Conversion ----------------

    def convert_doc(self, doc_file):
        self.progress.start()

        self.executor.submit(convert_doc_to_pdf, self.convert_doc_result, doc_file)

    def convert_doc_result(self, status, result):

        self.stop_progress()

        if status == "success":
            self.progress.start()
            self.executor.submit(self.sign_files, self.sign_files_result, [result])
        else:
            self.show_error(result)

    def convert_folder_docs(self, event=None):

        confirm = messagebox.askyesno(
            title="Επιβεβαίωση",
            message="Θα δημιουργηθούν PDF από όλα τα αρχεία κειμένου.\n\nΘέλετε να συνεχίσετε;",
        )

        if not confirm:
            return

        self.btn_sign.config(state="disabled")

        self.progress.start()
        self.executor.submit(
            convert_folder_docs_to_pdfs,
            self.convert_folder_docs_result,
            self.file_path,
        )

    def convert_folder_docs_result(self, status, result):

        self.stop_progress()

        if status == "success":
            msg = (
                f"Δημιουργήθηκαν {len(result['success'])} PDF αρχεία:\n"
                + "\n".join(result["success"])
                if result["success"]
                else "Δεν μετατράπηκαν αρχεία."
            )

            if result["fail"]:
                msg += "\n\nΑπέτυχαν:\n" + "\n".join(result["fail"])

            if result["ignore"]:
                msg += "\n\nΑγνοήθηκαν:\n" + "\n".join(result["ignore"])

            self.show_info(msg)
        else:
            self.show_error(result)

    # ---------------- Helpers ----------------

    def stop_progress(self):

        if self.progress.winfo_exists():
            self.progress.stop()

        if self.btn_sign.winfo_exists():
            self.btn_sign.config(state="normal")

    def autofill_password(self, event=None):

        username = self.get_username()

        saved = load_password(SERVICE_NAME, username)

        if saved:
            self.entry_pass.delete(0, tk.END)
            self.entry_pass.insert(0, saved)
            self.entry_otp.focus()

    def get_username(self):
        return self.entry_user.get().strip()

    def get_password(self):
        return self.entry_pass.get().strip()

    def get_otp(self):
        return self.entry_otp.get().strip()

    def show_info(self, msg):
        messagebox.showinfo("Πληροφορία", msg)

    def show_error(self, msg):
        messagebox.showerror("Σφάλμα", msg)
