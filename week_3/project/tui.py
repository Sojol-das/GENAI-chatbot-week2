"""TUI interface for Research Desk — Week 3."""
import threading
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Input, RichLog
from textual.containers import VerticalScroll

from agent import Agent


class TUIAgent(Agent):
    """Agent subclass that routes _emit() to the Textual log panel."""

    def __init__(self, *args, **kwargs):
        self._log_fn = None
        super().__init__(*args, **kwargs)

    def _emit(self, text: str) -> None:
        if self._log_fn:
            self._log_fn(f"[dim]{text}[/dim]")


class ResearchDeskApp(App):
    CSS = """
    Screen {
        layout: vertical;
    }
    RichLog {
        border: solid $primary;
        height: 1fr;
        padding: 1 2;
    }
    Input {
        dock: bottom;
        height: 3;
        border: solid $accent;
    }
    """

    TITLE = "CSOT Week 3 — Research Desk"
    BINDINGS = [
        ("ctrl+q", "quit", "Quit"),
        ("ctrl+l", "clear_log", "Clear log"),
        ("ctrl+k", "clear_input", "Clear input"),
    ]

    def __init__(self, agent: TUIAgent):
        super().__init__()
        self.agent = agent

    def compose(self) -> ComposeResult:
        yield Header()
        with VerticalScroll():
            yield RichLog(highlight=True, markup=True, wrap=True, id="log")
        yield Input(placeholder="Ask a question… (Enter to send)", id="query")
        yield Footer()

    def on_mount(self) -> None:
        log = self.query_one(RichLog)
        log.write(f"[bold]Research Desk[/bold]  session [cyan]{self.agent.session_id}[/cyan]")
        log.write(
            "[dim]Tools: web_search · web_fetch · paper_search · read_paper "
            "· read_file · write_file · edit_file · list_files[/dim]\n"
        )
        self.agent._log_fn = lambda t: self.call_from_thread(log.write, t)
        self.query_one(Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        question = event.value.strip()
        if not question:
            return
        self.query_one(Input).value = ""
        log = self.query_one(RichLog)
        log.write(f"\n[bold magenta]You:[/bold magenta] {question}")
        log.write("[dim]Thinking…[/dim]")
        self.agent._log_fn = lambda t: self.call_from_thread(log.write, t)

        def _run():
            try:
                answer = self.agent.chat(question)
                self.call_from_thread(
                    log.write,
                    f"\n[bold green]Assistant:[/bold green]\n{answer}\n",
                )
            except Exception as e:
                self.call_from_thread(log.write, f"[red][ERROR] {e}[/red]")

        threading.Thread(target=_run, daemon=True).start()

    def action_clear_log(self) -> None:
        self.query_one(RichLog).clear()

    def action_clear_input(self) -> None:
        self.query_one(Input).value = ""
