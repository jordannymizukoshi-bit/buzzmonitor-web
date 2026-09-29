"""Login no Buzzmonitor e, para cada linha da planilha (a partir da linha 2),
abre o link da coluna A, preenche o campo de resposta com o texto da coluna B
e clica em "Enviar". Roda em loop até esgotar as linhas da planilha.

Detecta quando a sessão do Buzzmonitor cai (redirecionamento de volta para a
tela de login) e avisa o usuário (som + banner no console) para logar de novo,
retomando a partir do mesmo ticket."""

import winsound

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError

from src.browser import get_browser
from src.sheets import get_worksheet

LOGIN_URL = "https://app.buzzmonitor.com.br/user/session/new"
LOGIN_TIMEOUT = 120000  # 120 segundos

PAGE_LOAD_WAIT_MS = 10000  # espera após abrir o link do ticket
TEXTAREA_TIMEOUT_MS = 20000

REPLY_TEXTAREA_SELECTOR = "textarea#reply-message.reply-message"
SEND_BUTTON_SELECTOR = "input#send-reply-button.bt-action-reply"
# Seletor do input de busca de tags (dentro do painel que abre ao clicar no botão de tags)
TAG_SEARCH_INPUT_SELECTOR = 'input.tp-search-input[placeholder="Buscar por tags"]:visible'
TAG_APPLY_BUTTON_SELECTOR = "button.tp-apply:visible"
TAG_NAME = "DM. Buyer_Outros"
STATUS_DROPDOWN_TRIGGER = "div.ticket-area[data-ng-show='hasTickets'] #s2id_ticket-status a.select2-choice"
# O item "Resolvido" no dropdown do Select2
STATUS_OPTION_RESOLVIDO = "ul.select2-results li.select2-result-selectable div.select2-result-label:has-text('Resolvido')"

DEBUG_SCREENSHOT = "downloads/debug_reply_error.png"


def alert(message: str) -> None:
    """Chama a atenção do usuário: banner no console + som (Windows)."""
    banner = "!" * 70
    print(f"\n{banner}\n{message}\n{banner}\n")
    try:
        winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
    except Exception:
        pass  # ambiente sem suporte a som; o banner no console já avisa


def is_login_page(page: Page) -> bool:
    return "/user/session" in page.url or "/login" in page.url


def wait_for_login(page: Page) -> bool:
    """Aguarda o usuário logar (redirecionamento para /folders). Retorna True se logou."""
    print("  Aguardando login do usuário (timeout de "
          f"{LOGIN_TIMEOUT // 1000}s)...\n")
    try:
        page.wait_for_url("**/folders**", timeout=LOGIN_TIMEOUT)
        print("✓ Login detectado!\n")
        return True
    except PlaywrightTimeoutError:
        return False


def ensure_logged_in(page: Page) -> bool:
    """Garante que há uma sessão válida, pedindo login se necessário."""
    page.goto(LOGIN_URL)
    return wait_for_login(page)


def _wait_and_click(page: Page, selector: str, step_description: str, link: str) -> str | None:
    """Espera o seletor ficar disponível e clica.

    Retorna None se deu certo, ou "session_expired"/"error" em caso de falha.
    """
    try:
        page.wait_for_selector(selector, timeout=TEXTAREA_TIMEOUT_MS)
    except PlaywrightTimeoutError:
        if is_login_page(page):
            return "session_expired"
        page.screenshot(path=DEBUG_SCREENSHOT, full_page=True)
        alert(
            f"ERRO: {step_description} não encontrado.\n"
            f"Link: {link}\n"
            f"Screenshot salvo em: {DEBUG_SCREENSHOT}"
        )
        return "error"
    page.click(selector)
    return None


def process_ticket(page: Page, link: str, reply_text: str) -> str:
    """Abre o link do ticket e preenche a resposta.

    Retorna "ok", "session_expired" ou "error".
    """
    page.goto(link)

    if is_login_page(page):
        return "session_expired"

    page.wait_for_timeout(PAGE_LOAD_WAIT_MS)

    if is_login_page(page):
        return "session_expired"

    try:
        page.wait_for_selector(REPLY_TEXTAREA_SELECTOR, timeout=TEXTAREA_TIMEOUT_MS)
    except PlaywrightTimeoutError:
        if is_login_page(page):
            return "session_expired"
        page.screenshot(path=DEBUG_SCREENSHOT, full_page=True)
        alert(
            "ERRO: campo de resposta não encontrado.\n"
            f"Link: {link}\n"
            f"Screenshot salvo em: {DEBUG_SCREENSHOT}"
        )
        return "error"

    page.fill(REPLY_TEXTAREA_SELECTOR, reply_text)

    result = _wait_and_click(page, SEND_BUTTON_SELECTOR, "botão de enviar", link)
    if result:
        return result

    # Aguarda o envio ser concluído: espera o campo de resposta esvaziar,
    # o que indica que o Buzzmonitor processou o envio com sucesso.
    # (O toast "Enviando resposta..." desaparece e o campo fica vazio.)
    print("  Aguardando confirmação de envio...")
    try:
        page.wait_for_function(
            "!document.querySelector('textarea#reply-message') || "
            "document.querySelector('textarea#reply-message').value === ''",
            timeout=30000,
        )
    except PlaywrightTimeoutError:
        page.wait_for_timeout(3000)  # fallback se a verificação falhar

    # ── Tags: clicar no botão para abrir o modal de tags do ticket ──────────────
    # O botão correto (do ticket) tem sempre um div#block-tag-button como irmão
    # imediato no HTML — o botão da toolbar NÃO tem esse irmão.
    # Seletor CSS: "#block-tag-button ~ a.button.tags"
    TAG_BUTTON_SELECTOR = 'div.ticket-area[data-ng-show="hasTickets"] #block-tag-button ~ a.button.tags'

   # ── 1. Clica no botão para abrir o modal de tags ──────────────────────────────
    print("  [tags 1/3] Abrindo modal de tags do ticket...")
    try:
        page.wait_for_selector(TAG_BUTTON_SELECTOR, state="visible", timeout=TEXTAREA_TIMEOUT_MS)
    except PlaywrightTimeoutError:
        if is_login_page(page):
            return "session_expired"
        page.screenshot(path=DEBUG_SCREENSHOT, full_page=True)
        alert(
            "ERRO: botão de tags do ticket não encontrado.\n"
            f"Link: {link}\n"
            f"Screenshot salvo em: {DEBUG_SCREENSHOT}"
        )
        return "error"
    page.click(TAG_BUTTON_SELECTOR)
    page.wait_for_timeout(600)

    # ── 2. Digita o nome da tag no campo de busca ────────────────────────────────
    print(f"  [tags 2/3] Digitando '{TAG_NAME}' no campo de busca...")
    try:
        page.wait_for_selector(TAG_SEARCH_INPUT_SELECTOR, state="visible", timeout=TEXTAREA_TIMEOUT_MS)
    except PlaywrightTimeoutError:
        if is_login_page(page):
            return "session_expired"
        page.screenshot(path=DEBUG_SCREENSHOT, full_page=True)
        alert(
            "ERRO: campo de busca de tags não apareceu após abrir o modal.\n"
            f"Link: {link}\n"
            f"Screenshot salvo em: {DEBUG_SCREENSHOT}"
        )
        return "error"
    page.fill(TAG_SEARCH_INPUT_SELECTOR, TAG_NAME)
    page.wait_for_timeout(1200)

    # Seleciona a tag visível
    print(f"  [tags 2/3] Selecionando a tag '{TAG_NAME}'...")
    tag_row = page.locator("div.tp-row.tp-tag:visible").filter(has_text=TAG_NAME).first
    try:
        tag_row.wait_for(state="visible", timeout=TEXTAREA_TIMEOUT_MS)
    except PlaywrightTimeoutError:
        if is_login_page(page):
            return "session_expired"
        page.screenshot(path=DEBUG_SCREENSHOT, full_page=True)
        alert(
            f"ERRO: tag '{TAG_NAME}' não encontrada na lista.\n"
            f"Link: {link}\n"
            f"Screenshot salvo em: {DEBUG_SCREENSHOT}"
        )
        return "error"
    tag_row.locator("span.tp-check.tp-check--tag").click()

    # ── 3. Clica em "Aplicar" ────────────────────────────────────────────────────
    print("  [tags 3/3] Clicando em Aplicar...")
    try:
        apply_btn = page.locator(TAG_APPLY_BUTTON_SELECTOR)
        apply_btn.wait_for(state="visible", timeout=TEXTAREA_TIMEOUT_MS)
        apply_btn.click(timeout=TEXTAREA_TIMEOUT_MS)
    except PlaywrightTimeoutError:
        if is_login_page(page):
            return "session_expired"
        page.screenshot(path=DEBUG_SCREENSHOT, full_page=True)
        alert(
            "ERRO: botão 'Aplicar' não apareceu ou falhou ao ser clicado.\n"
            f"Link: {link}\n"
            f"Screenshot salvo em: {DEBUG_SCREENSHOT}"
        )
        return "error"

    # Aguarda o modal sumir completamente antes de prosseguir
    page.wait_for_timeout(1500)

    # ── 4. Muda o status do ticket para "Resolvido" ──────────────────────────
    print("  [status 1/2] Abrindo dropdown de status...")
    result = _wait_and_click(page, STATUS_DROPDOWN_TRIGGER, "dropdown de status", link)
    if result:
        return result

    # Aguarda a renderização das opções do Select2 na tela
    page.wait_for_timeout(500)

    print("  [status 2/2] Selecionando 'Resolvido'...")
    result = _wait_and_click(page, STATUS_OPTION_RESOLVIDO, 'opção "Resolvido" no dropdown de status', link)
    if result:
        return result

    page.wait_for_timeout(1000)
    return "ok"



def main() -> None:
    print("Lendo planilha do Google Sheets...")
    worksheet = get_worksheet()
    rows = worksheet.get_all_values()[1:]  # pula o cabeçalho (linha 1)

    tickets = [
        (row_num, row[0], row[1])
        for row_num, row in enumerate(rows, start=2)
        if len(row) >= 2 and row[0].strip()
    ]

    if not tickets:
        print("⚠ Nenhum ticket encontrado na planilha (colunas A/B a partir da linha 2).")
        return

    print(f"✓ {len(tickets)} ticket(s) encontrado(s) na planilha.\n")
    print("Iniciando Buzzmonitor...")

    with get_browser(headless=False) as browser:
        page = browser.new_page()

        print("\n✓ Página de login aberta.")
        if not ensure_logged_in(page):
            alert(f"⚠ Timeout esperando login inicial (após {LOGIN_TIMEOUT // 1000}s). Script encerrado.")
            return

        index = 0
        while index < len(tickets):
            row_num, link, reply_text = tickets[index]
            print(f"--- Ticket {index + 1}/{len(tickets)} (linha {row_num}) ---")
            print(f"Link: {link}")

            result = process_ticket(page, link, reply_text)

            if result == "session_expired":
                alert(
                    "SESSÃO EXPIRADA! Faça login novamente no navegador.\n"
                    f"O script retomará automaticamente no ticket da linha {row_num}."
                )
                if not ensure_logged_in(page):
                    alert(f"⚠ Timeout esperando novo login (após {LOGIN_TIMEOUT // 1000}s). Script encerrado.")
                    return
                continue  # tenta o mesmo ticket de novo

            if result == "error":
                choice = input(
                    "  Digite 'r' para tentar de novo, 's' para pular este ticket, "
                    "ou 'a' para abortar: "
                ).strip().lower()
                if choice == "r":
                    continue
                if choice == "a":
                    print("Script abortado pelo usuário.")
                    return
                print("  Pulando este ticket.\n")
                index += 1
                continue

            # result == "ok"
            print("✓ Resposta enviada automaticamente.\n")
            index += 1

        print("Todos os tickets foram processados.")
        input("Pressione ENTER para encerrar (isso fechará o navegador)...")


if __name__ == "__main__":
    main()
