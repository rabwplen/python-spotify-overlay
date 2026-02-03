import customtkinter as ctk

from utils import save_settings

class SettingsWindow(ctk.CTkToplevel):
    def __init__(self, overlay):
        super().__init__()
        self.overlay = overlay

        self.title("Overlay Settings")
        self.geometry("400x350")
        self.resizable(False, False)
        self.configure(fg_color="#00141B")

        def on_close():
            self.overlay.settings_openned = False
            self.destroy()
            save_settings({
                "default_opacity": self.overlay.default_opacity,
                "hover_opacity": self.overlay.hover_opacity,
                "fade_delay": self.overlay.fade_delay,
                "fade_duration": self.overlay.fade_duration,
                "always_on_top": self.overlay.always_on_top,
                "can_drag": self.overlay.can_drag,
                "click_through": self.overlay.click_through
            })

        self.protocol("WM_DELETE_WINDOW", on_close)



        # Slider opacity
        opacity_label = ctk.CTkLabel(self, text=f"Window opacity: {self.overlay.default_opacity:.1f}")
        opacity_label.place(y=10, x=8)

        opacity_slider = ctk.CTkSlider(self, from_=0.1, to=1.0, number_of_steps=9, width=130)
        opacity_slider.set(self.overlay.default_opacity)
        opacity_slider.place(y=10+4.5, x=-15, relx=1, anchor="ne")

        def update_opacity(value):
            self.overlay.default_opacity = float(value)
            opacity_label.configure(text=f"Window opacity: {float(value):.1f}")
            if not self.overlay.inside:
                self.overlay.fade_to(self.overlay.default_opacity)
        opacity_slider.configure(command=update_opacity)

        # Slider opacity-on-hover
        opacityOnHover_label = ctk.CTkLabel(self, text=f"Window opacity on hover: {self.overlay.hover_opacity:.1f}")
        opacityOnHover_label.place(y=40, x=8)

        opacityOnHover_slider = ctk.CTkSlider(self, from_=0.1, to=1.0, number_of_steps=9, width=130)
        opacityOnHover_slider.set(self.overlay.hover_opacity)
        opacityOnHover_slider.place(y=40+4.5, x=-15, relx=1, anchor="ne")

        def update_opacityOnHover(value):
            self.overlay.hover_opacity = float(value)
            opacityOnHover_label.configure(text=f"Window opacity on hover: {float(value):.1f}")
            if not self.overlay.inside:
                self.overlay.fade_to(self.overlay.default_opacity)
        opacityOnHover_slider.configure(command=update_opacityOnHover)

        # Slider fade-delay
        fadeDelay_label = ctk.CTkLabel(self, text=f"Fade delay: {self.overlay.fade_delay:.1f}")
        fadeDelay_label.place(y=70, x=8)

        fadeDelay_slider = ctk.CTkSlider(self, from_=1, to=10, number_of_steps=9, width=130)
        fadeDelay_slider.set(self.overlay.fade_delay)
        fadeDelay_slider.place(y=70+4.5, x=-15, relx=1, anchor="ne")

        def update_fadeDelay(value):
            self.overlay.fade_delay = float(value)
            fadeDelay_label.configure(text=f"Fade delay: {float(value):.1f}")
            if not self.overlay.inside:
                self.overlay.fade_to(self.overlay.fade_delay)
        fadeDelay_slider.configure(command=update_fadeDelay)

        # Slider fade-duration
        fadeDuration_label = ctk.CTkLabel(self, text=f"Fade duration: {self.overlay.fade_duration:.1f}")
        fadeDuration_label.place(y=100, x=8)

        fadeDuration_slider = ctk.CTkSlider(self, from_=0.1, to=5, number_of_steps=49, width=130)
        fadeDuration_slider.set(self.overlay.fade_duration)
        fadeDuration_slider.place(y=100+4.5, x=-15, relx=1, anchor="ne")

        def update_fadeDuration(value):
            self.overlay.fade_duration = float(value)
            fadeDuration_label.configure(text=f"Fade duration: {float(value):.1f}")
            if not self.overlay.inside:
                self.overlay.fade_to(self.overlay.fade_duration)
        fadeDuration_slider.configure(command=update_fadeDuration)

        # Toggle always-on-top
        def toggle_top(value):
            self.overlay.always_on_top = value
            self.overlay.attributes("-topmost", self.overlay.always_on_top)

        top_switch = ctk.CTkSwitch(self, text="Always on top", command=lambda: toggle_top(top_switch.get()))
        if self.overlay.always_on_top: top_switch.select()
        top_switch.place(y=130, x=8)

        # Toggle can-drag
        def toggle_canDrag(value):
            self.overlay.can_drag = value

        canDrag_switch = ctk.CTkSwitch(self, text="Can drag", command=lambda: toggle_canDrag(canDrag_switch.get()))
        if self.overlay.can_drag: canDrag_switch.select()
        canDrag_switch.place(y=160, x=8)

        # Toggle click-through
        def toggle_click_through(value):
            self.overlay.click_through = value
            self.overlay.set_click_through(self.overlay.click_through)
            
            self.overlay.settings_toggle_click_through()

            # save immediately after changing
            save_settings({
                "default_opacity": self.overlay.default_opacity,
                "hover_opacity": self.overlay.hover_opacity,
                "fade_delay": self.overlay.fade_delay,
                "fade_duration": self.overlay.fade_duration,
                "always_on_top": self.overlay.always_on_top,
                "can_drag": self.overlay.can_drag,
                "click_through": self.overlay.click_through
            })

        click_through_switch = ctk.CTkSwitch(self, text="Click-Through", command=lambda: toggle_click_through(click_through_switch.get()))
        if self.overlay.click_through: click_through_switch.select()
        click_through_switch.place(y=190, x=8)