# -*- mode: python ; coding: utf-8 -*-
# Información de versión incrustada en el ejecutable (Propiedades de Windows).
# Los campos numéricos (FILEVERSION/PRODUCTVERSION) deben ser 4 enteros;
# los campos de texto pueden llevar el sufijo de fase (beta).

VSVersionInfo(
    ffi=FixedFileInfo(
        filevers=(0, 6, 3, 0),
        prodvers=(0, 6, 3, 0),
        mask=0x3F,
        flags=0x0,
        OS=0x40004,          # VOS_NT_WINDOWS32
        fileType=0x1,        # VFT_APP
        subtype=0x0,
        date=(0, 0),
    ),
    kids=[
        StringFileInfo(
            [
                StringTable(
                    '040904B0',   # Inglés (EE.UU.), Unicode
                    [
                        StringStruct('CompanyName', 'Jhon D. Velez & Jeisson I. Sanchez'),
                        StringStruct('FileDescription', 'OpenBotV Studio'),
                        StringStruct('FileVersion', 'v0.6.3-beta'),
                        StringStruct('InternalName', 'OpenBotV-Studio'),
                        StringStruct('LegalCopyright', 'Jhon D. Velez & Jeisson I. Sanchez'),
                        StringStruct('OriginalFilename', 'OpenBotV-Studio.exe'),
                        StringStruct('ProductName', 'OpenBotV Studio'),
                        StringStruct('ProductVersion', 'v0.6.3-beta'),
                    ],
                )
            ]
        ),
        VarFileInfo([VarStruct('Translation', [1033, 1200])]),
    ],
)
