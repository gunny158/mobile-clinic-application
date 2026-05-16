"""Mobile Clinic — entry point."""
import customtkinter as ctk
from database.connection import get_connection


def main() -> None:
    # Initialise database (creates file + schema on first run)
    get_connection()

    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")

    root = ctk.CTk()
    root.withdraw()   # hidden controller window; child Toplevel windows are visible
    root.title("Mobile Clinic")

    def show_login() -> None:
        from ui.login import LoginWindow
        LoginWindow(root, on_success=on_login)

    def on_login(user: dict) -> None:
        from ui.main_window import MainWindow
        container: list = [None]

        def do_signout() -> None:
            if container[0]:
                container[0].destroy()
                container[0] = None
            show_login()

        main_win = MainWindow(root, user, on_signout=do_signout)
        container[0] = main_win
        main_win.protocol("WM_DELETE_WINDOW", root.quit)
        main_win.focus()

    show_login()
    root.mainloop()


if __name__ == "__main__":
    main()
