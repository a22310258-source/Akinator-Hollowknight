#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Akinator de Hollow Knight — GUI (Tkinter, fondo difuminado)
-----------------------------------------------------------
- Solo respuestas: Sí / No (se eliminó "Tal vez").
- Fondo con imagen difuminada (GaussianBlur) que se reescala dinámicamente.
- Panel semitransparente para legibilidad.
- Exportar / Importar conocimiento, estadísticas y aprendizaje.

Requisitos: Pillow (PIL)
    pip install pillow

Ejecuta:
    python hollow_akinator_gui_blur.py
"""

import json
import os
from typing import Dict, Any, Optional
import tkinter as tk
from tkinter import messagebox, simpledialog, filedialog
from PIL import Image, ImageTk, ImageFilter

DATA_FILE = "hk_knowledge.json"
STATS_FILE = "hk_stats.json"
BACKGROUND_IMAGE = "hk_bg.png"


def default_tree() -> Dict[str, Any]:
    return {
        "q": "¿Es un jefe o te enfrentas a él/ella en combate principal?",
        "yes": {
            "q": "¿Es una entidad divina o regente del Reino?",
            "yes": {
                "q": "¿Está asociada directamente a la luz y los sueños?",
                "yes": {"guess": "Radiancia"},
                "no": {"guess": "Rey Pálido"},
            },
            "no": {
                "q": "¿Se presenta en plural o en equipo durante el combate?",
                "yes": {"guess": "Señores Mantis"},
                "no": {
                    "q": "¿Usa una aguja e hilo en combate?",
                    "yes": {"guess": "Hornet"},
                    "no": {
                        "q": "¿Lidera una troupe y es teatral?",
                        "yes": {"guess": "Grimm"},
                        "no": {
                            "q": "¿Es un recipiente silencioso sellado?",
                            "yes": {"guess": "Hollow Knight"},
                            "no": {"guess": "Nosk"},
                        },
                    },
                },
            },
        },
        "no": {
            "q": "¿Es cartógrafo y tararea mientras hace mapas?",
            "yes": {"guess": "Cornifer"},
            "no": {
                "q": "¿Es fanfarrón y presume 57 preceptos?",
                "yes": {"guess": "Zote el Poderoso"},
                "no": {
                    "q": "¿Es un artista y maestro del aguijón retirado?",
                    "yes": {"guess": "Maestro del Aguijón Sheo"},
                    "no": {
                        "q": "¿Es aventurera con gran armadura?",
                        "yes": {"guess": "Cloth"},
                        "no": {
                            "q": "¿Es un explorador amable con casco azul?",
                            "yes": {"guess": "Quirrel"},
                            "no": {
                                "q": "¿Es una joven romántica que admira a Zote?",
                                "yes": {"guess": "Bretta"},
                                "no": {
                                    "q": "¿Busca gloria en el coliseo y tiene un destino trágico?",
                                    "yes": {"guess": "Tiso"},
                                    "no": {"guess": "El Caballero"},
                                },
                            },
                        },
                    },
                },
            },
        },
    }


def load_tree() -> Dict[str, Any]:
    if not os.path.exists(DATA_FILE):
        t = default_tree()
        save_tree(t)
        return t
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_tree(tree: Dict[str, Any]) -> None:
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(tree, f, ensure_ascii=False, indent=2)


def load_stats() -> Dict[str, int]:
    if not os.path.exists(STATS_FILE):
        stats = {"played": 0, "wins": 0, "learned": 0}
        save_stats(stats)
        return stats
    with open(STATS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_stats(stats: Dict[str, int]) -> None:
    with open(STATS_FILE, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)


def is_leaf(node: Dict[str, Any]) -> bool:
    return isinstance(node, dict) and "guess" in node


def normalize_question(q: str) -> str:
    q = q.strip()
    if not q.endswith("?"):
        q += "?"
    return q


class GameState:
    def __init__(self, tree: Dict[str, Any]):
        self.tree = tree
        self.path = []
        self.node = tree

    def restart(self):
        self.path.clear()
        self.node = self.tree

    def answer(self, ans: str) -> None:
        if is_leaf(self.node):
            return
        branch = "yes" if ans == "yes" else "no"
        self.path.append((self.node, branch))
        self.node = self.node.get(branch, {})

    def current_text(self) -> str:
        if is_leaf(self.node):
            return f"¿Tu personaje es **{self.node['guess']}**?"
        return self.node.get("q", "¿...?")

    def learn(self, true_name: str, new_question: str, answer_yes_for_new: bool):
        if not is_leaf(self.node):
            return
        old_guess = self.node["guess"]
        new_node = {
            "q": normalize_question(new_question),
            "yes": {"guess": true_name} if answer_yes_for_new else {"guess": old_guess},
            "no": {"guess": old_guess} if answer_yes_for_new else {"guess": true_name},
        }
        if not self.path:
            self.tree = new_node
            self.node = new_node
        else:
            parent, side = self.path[-1]
            parent[side] = new_node
            self.node = new_node
        save_tree(self.tree)


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Akinator de Hollow Knight")
        self.geometry("820x480")
        self.minsize(720, 420)

        self.tree = load_tree()
        self.state = GameState(self.tree)
        self.stats = load_stats()

        # Fondo
        self._bg_original = None
        self._bg_image = None
        self._load_background()

        # Canvas para fondo
        self.canvas = tk.Canvas(self, highlightthickness=0, bd=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", self._on_resize)

        # Construcción UI
        self._build_menu()
        self._build_widgets()
        self._render()

    # ---------- Fondo ----------
    def _load_background(self):
        try:
            if os.path.exists(BACKGROUND_IMAGE):
                from PIL import Image
                self._bg_original = Image.open(BACKGROUND_IMAGE).convert("RGB")
        except Exception:
            self._bg_original = None

    def _draw_background(self, w: int, h: int):
        self.canvas.delete("bg")
        if not self._bg_original:
            self.canvas.create_rectangle(0, 0, w, h, fill="#0b1020", outline="", tags="bg")
            return

        from PIL import Image, ImageTk, ImageFilter
        img = self._bg_original.copy()
        img_ratio = img.width / img.height
        canvas_ratio = w / h if h else 1.0

        if canvas_ratio > img_ratio:
            new_w = w
            new_h = int(w / img_ratio)
        else:
            new_h = h
            new_w = int(h * img_ratio)

        img = img.resize((max(1, new_w), max(1, new_h)), Image.LANCZOS)
        img = img.filter(ImageFilter.GaussianBlur(radius=10))

        x0 = (img.width - w) // 2 if img.width > w else 0
        y0 = (img.height - h) // 2 if img.height > h else 0
        img = img.crop((x0, y0, x0 + w, y0 + h))

        self._bg_image = ImageTk.PhotoImage(img)
        self.canvas.create_image(0, 0, image=self._bg_image, anchor="nw", tags="bg")

        # Rectángulo con patrón para simular transparencia alrededor (estético)
        panel_pad = 20
        self.canvas.create_rectangle(
            panel_pad, panel_pad, w - panel_pad, h - panel_pad,
            fill="#000000", stipple="gray25", outline="", tags="bg"
        )

    def _on_resize(self, event):
        self._draw_background(event.width, event.height)
        self._place_panel(event.width, event.height)

    # ---------- UI ----------
    def _build_menu(self):
        menubar = tk.Menu(self)

        juego = tk.Menu(menubar, tearoff=0)
        juego.add_command(label="Nueva partida", command=self.new_game)
        juego.add_separator()
        juego.add_command(label="Exportar conocimiento…", command=self.export_tree)
        juego.add_command(label="Importar conocimiento…", command=self.import_tree)
        juego.add_separator()
        juego.add_command(label="Restablecer a valores iniciales", command=self.reset_default)
        juego.add_separator()
        juego.add_command(label="Salir", command=self.destroy)
        menubar.add_cascade(label="Juego", menu=juego)

        ver = tk.Menu(menubar, tearoff=0)
        ver.add_command(label="Ver estadísticas", command=self.show_stats)
        menubar.add_cascade(label="Ver", menu=ver)

        self.config(menu=menubar)

    def _build_widgets(self):
        # Panel
        self.panel_inner = tk.Frame(self.canvas, bg="#121212")
        self.label = tk.Label(self.panel_inner, text="", wraplength=620, justify="left",
                              font=("Segoe UI", 13, "bold"), fg="#FFFFFF", bg="#121212")
        self.label.pack(padx=18, pady=(18, 8), anchor="w")

        self.entry = tk.Entry(self.panel_inner, font=("Segoe UI", 12))
        self.entry.pack(padx=18, fill="x")
        self.entry.bind("<Return>", self.on_enter)

        btn_frame = tk.Frame(self.panel_inner, bg="#121212")
        btn_frame.pack(pady=14)

        self.btn_yes = tk.Button(btn_frame, text="Sí", width=12, command=lambda: self.on_button("yes"))
        self.btn_no = tk.Button(btn_frame, text="No", width=12, command=lambda: self.on_button("no"))

        self.btn_yes.grid(row=0, column=0, padx=10)
        self.btn_no.grid(row=0, column=1, padx=10)

        self.status = tk.Label(self.panel_inner, text="", anchor="w", justify="left",
                               fg="#D0D0D0", bg="#121212")
        self.status.pack(fill="x", padx=18, pady=(6, 14))

        self.panel_window = self.canvas.create_window(0, 0, window=self.panel_inner, anchor="center")

    def _place_panel(self, w, h):
        panel_w = min(700, int(w * 0.85))
        panel_h = min(360, int(h * 0.7))
        self.canvas.itemconfig(self.panel_window, width=panel_w, height=panel_h)
        self.canvas.coords(self.panel_window, w/2, h/2)

    def normalize_input(self, s: str) -> Optional[str]:
        s = s.strip().lower()
        if not s:
            return None
        yes = {"s", "si", "sí", "y", "yes"}
        no = {"n", "no"}
        if s in yes: return "yes"
        if s in no: return "no"
        return None

    def on_enter(self, event=None):
        text = self.entry.get()
        self.entry.delete(0, tk.END)
        normalized = self.normalize_input(text)
        if normalized is None:
            messagebox.showinfo("Ayuda", "Responde 'sí' o 'no'. También puedes usar los botones.")
            return
        self.on_button(normalized)

    def on_button(self, which: str):
        if is_leaf(self.state.node):
            guess = self.state.node["guess"]
            if which == "yes":
                self.stats["played"] += 1
                self.stats["wins"] += 1
                save_stats(self.stats)
                messagebox.showinfo("¡Adiviné!", f"🎉 ¡Genial! Era {guess}.")
                self.new_game()
                return
            else:
                self.learn_dialog(guess)
                return

        self.state.answer(which)
        self.label.config(text=self.state.current_text())
        self._update_status()

    def learn_dialog(self, wrong_guess: str):
        true_name = simpledialog.askstring("Aprender", "No lo adiviné.\n¿Cuál era tu personaje?")
        if not true_name:
            return
        q = simpledialog.askstring(
            "Nueva pregunta",
            f"Dame una pregunta SÍ/NO que distinga a '{true_name}' de '{wrong_guess}'.\n"
            "Ej.: '¿Es cartógrafo?', '¿Lidera una troupe?', '¿Usa aguja e hilo?'"
        )
        if not q:
            return
        ans = messagebox.askyesno("Respuesta para tu personaje",
                                  f"Para tu personaje '{true_name}', ¿la respuesta a esa pregunta es SÍ?")
        self.state.learn(true_name.strip(), q.strip(), ans)
        self.stats["played"] += 1
        self.stats["learned"] = self.stats.get("learned", 0) + 1
        save_tree(self.state.tree)
        save_stats(self.stats)
        messagebox.showinfo("Aprendido", "✅ He actualizado mi conocimiento con tu personaje.")
        self.new_game()

    def new_game(self):
        self.state = GameState(self.state.tree)
        self.label.config(text=self.state.current_text())
        self.entry.delete(0, tk.END)
        w = self.winfo_width() or 820
        h = self.winfo_height() or 480
        self._draw_background(w, h)
        self._place_panel(w, h)
        self._update_status()

    def _render(self):
        w = self.winfo_width() or 820
        h = self.winfo_height() or 480
        self._draw_background(w, h)
        self._place_panel(w, h)
        self.label.config(text=self.state.current_text())
        self._update_status()

    def _update_status(self):
        played = self.stats.get("played", 0)
        wins = self.stats.get("wins", 0)
        learned = self.stats.get("learned", 0)
        acc = (wins / played * 100) if played else 0.0
        self.status.config(text=f"Partidas: {played} | Aciertos: {wins} | Aprendidos: {learned} | Precisión: {acc:.1f}%")

    def show_stats(self):
        played = self.stats.get("played", 0)
        wins = self.stats.get("wins", 0)
        learned = self.stats.get("learned", 0)
        acc = (wins / played * 100) if played else 0.0
        msg = (
            f"📊 Estadísticas\n\n"
            f"Partidas jugadas: {played}\n"
            f"Aciertos: {wins}\n"
            f"Aprendidos: {learned}\n"
            f"Precisión: {acc:.1f}%\n"
        )
        messagebox.showinfo("Estadísticas", msg)

    def export_tree(self):
        path = filedialog.asksaveasfilename(
            title="Exportar conocimiento", defaultextension=".json",
            filetypes=[("JSON", "*.json"), ("Todos los archivos", "*.*")],
            initialfile="hk_knowledge_export.json"
        )
        if not path: return
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.state.tree, f, ensure_ascii=False, indent=2)
            messagebox.showinfo("Exportado", f"Conocimiento exportado a:\n{path}")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo exportar:\n{e}")

    def import_tree(self):
        path = filedialog.askopenfilename(
            title="Importar conocimiento", filetypes=[("JSON", "*.json"), ("Todos los archivos", "*.*")]
        )
        if not path: return
        try:
            with open(path, "r", encoding="utf-8") as f:
                new_tree = json.load(f)
            if not isinstance(new_tree, dict) or not ("q" in new_tree or "guess" in new_tree):
                raise ValueError("El archivo no parece un árbol de decisiones válido.")
            self.state.tree = new_tree
            save_tree(new_tree)
            self.new_game()
            messagebox.showinfo("Importado", "Conocimiento importado y guardado.")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo importar:\n{e}")

    def reset_default(self):
        ok = messagebox.askyesno("Restablecer", "¿Seguro que quieres restablecer el conocimiento a la versión inicial?")
        if not ok: return
        t = default_tree()
        save_tree(t)
        self.state.tree = t
        self.new_game()


if __name__ == "__main__":
    app = App()
    app.mainloop()
