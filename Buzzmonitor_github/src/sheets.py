"""Inicialização do gspread para acesso ao Google Sheets."""

import os

from dotenv import load_dotenv

load_dotenv()

import gspread
from gspread import Worksheet

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def get_client(credentials_path: str | None = None) -> gspread.Client:
    """Autentica no Google Sheets via conta de serviço e retorna o cliente gspread.

    credentials_path: caminho do JSON da conta de serviço. Se omitido, usa a
    variável de ambiente GOOGLE_CREDENTIALS_PATH.
    """
    path = credentials_path or os.environ.get("GOOGLE_CREDENTIALS_PATH")
    if not path:
        raise ValueError(
            "Informe credentials_path ou defina GOOGLE_CREDENTIALS_PATH no ambiente."
        )
    return gspread.service_account(filename=path, scopes=SCOPES)


def get_worksheet(
    sheet_id: str | None = None,
    worksheet_name: str | None = None,
    credentials_path: str | None = None,
) -> Worksheet:
    """Abre uma planilha pelo ID e retorna a aba (worksheet) desejada.

    Os parâmetros omitidos caem para as variáveis de ambiente GOOGLE_SHEET_ID
    e GOOGLE_WORKSHEET_NAME.
    """
    client = get_client(credentials_path)

    sid = sheet_id or os.environ.get("GOOGLE_SHEET_ID")
    if not sid:
        raise ValueError("Informe sheet_id ou defina GOOGLE_SHEET_ID no ambiente.")

    spreadsheet = client.open_by_key(sid)

    name = worksheet_name or os.environ.get("GOOGLE_WORKSHEET_NAME")
    return spreadsheet.worksheet(name) if name else spreadsheet.sheet1
