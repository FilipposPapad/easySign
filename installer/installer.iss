[Setup]
AppName=easySign
AppVersion=0.9.0
DefaultDirName={pf}\easySign
DefaultGroupName=easySign
OutputDir=.
OutputBaseFilename=easySignSetup
Compression=lzma
SolidCompression=yes

[Files]
Source: "dist\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs
Source: "..\src\config.json"; DestDir: "{app}"
Source: "..\src\resources\certs\byte.pem"; DestDir: "{app}\resources\certs"
Source: "..\src\resources\images\signclient.ico"; DestDir: "{app}\resources\images"
Source: "..\src\resources\images\signature.png"; DestDir: "{app}\resources\images"
Source: "..\src\resources\images\pdf.png"; DestDir: "{app}\resources\images"
Source: "..\src\resources\images\get.png"; DestDir: "{app}\resources\images"

[Registry]
Root: HKCR; Subkey: "SystemFileAssociations\.pdf\shell\SignWithEasy"; ValueType: string; ValueData: "Ψηφιακή Υπογραφή"; Flags: uninsdeletekey
Root: HKCR; Subkey: "SystemFileAssociations\.pdf\shell\SignWithEasy"; ValueName: "Icon"; ValueType: string; ValueData: "{app}\client\client.exe"
Root: HKCR; Subkey: "SystemFileAssociations\.pdf\shell\SignWithEasy\command"; ValueType: string; ValueData: """{app}\client\client.exe"" ""%1"""; Flags: uninsdeletekey

Root: HKCR; Subkey: "SystemFileAssociations\.doc\shell\SignWithEasy"; ValueType: string; ValueData: "Ψηφιακή Υπογραφή"; Flags: uninsdeletekey
Root: HKCR; Subkey: "SystemFileAssociations\.doc\shell\SignWithEasy"; ValueName: "Icon"; ValueType: string; ValueData: "{app}\client\client.exe"
Root: HKCR; Subkey: "SystemFileAssociations\.doc\shell\SignWithEasy\command"; ValueType: string; ValueData: """{app}\client\client.exe"" ""%1"""; Flags: uninsdeletekey

Root: HKCR; Subkey: "SystemFileAssociations\.docx\shell\SignWithEasy"; ValueType: string; ValueData: "Ψηφιακή Υπογραφή"; Flags: uninsdeletekey
Root: HKCR; Subkey: "SystemFileAssociations\.docx\shell\SignWithEasy"; ValueName: "Icon"; ValueType: string; ValueData: "{app}\client\client.exe"
Root: HKCR; Subkey: "SystemFileAssociations\.docx\shell\SignWithEasy\command"; ValueType: string; ValueData: """{app}\client\client.exe"" ""%1"""; Flags: uninsdeletekey

Root: HKCR; Subkey: "SystemFileAssociations\.odt\shell\SignWithEasy"; ValueType: string; ValueData: "Ψηφιακή Υπογραφή"; Flags: uninsdeletekey
Root: HKCR; Subkey: "SystemFileAssociations\.odt\shell\SignWithEasy"; ValueName: "Icon"; ValueType: string; ValueData: "{app}\client\client.exe"
Root: HKCR; Subkey: "SystemFileAssociations\.odt\shell\SignWithEasy\command"; ValueType: string; ValueData: """{app}\client\client.exe"" ""%1"""; Flags: uninsdeletekey

Root: HKCR; Subkey: "SystemFileAssociations\.rtf\shell\SignWithEasy"; ValueType: string; ValueData: "Ψηφιακή Υπογραφή"; Flags: uninsdeletekey
Root: HKCR; Subkey: "SystemFileAssociations\.rtf\shell\SignWithEasy"; ValueName: "Icon"; ValueType: string; ValueData: "{app}\client\client.exe"
Root: HKCR; Subkey: "SystemFileAssociations\.rtf\shell\SignWithEasy\command"; ValueType: string; ValueData: """{app}\client\client.exe"" ""%1"""; Flags: uninsdeletekey

Root: HKCR; Subkey: "Directory\shell\SignWithEasy"; ValueType: string; ValueData: "Ψηφιακή Υπογραφή"; Flags: uninsdeletekey
Root: HKCR; Subkey: "Directory\shell\SignWithEasy"; ValueName: "Icon"; ValueType: string; ValueData: "{app}\client\client.exe"
Root: HKCR; Subkey: "Directory\shell\SignWithEasy\command"; ValueType: string; ValueData: """{app}\client\client.exe"" ""%1"""; Flags: uninsdeletekey

[UninstallDelete]
Type: filesandordirs; Name: "{app}"