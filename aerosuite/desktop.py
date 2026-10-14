"""AeroSuite Airfoil Lab desktop application (Tkinter, no server required)."""
from __future__ import annotations

import json
from pathlib import Path
import queue
import threading
import uuid
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from .airfoil_lab_core import (BatchRequest, data_directory, download_uiuc,
    download_xfoil, official_uiuc_path, official_xfoil_path, run_batch, uiuc_ids)
from .xfoil_cli import XFoilCase


class AirfoilLab(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("AeroSuite | Airfoil Lab")
        self.geometry("1160x800")
        self.minsize(940,630)
        self.events = queue.Queue()
        self.busy = False
        self.solver = tk.StringVar(value=str(official_xfoil_path()))
        self.uiuc = tk.StringVar(value=str(official_uiuc_path()))
        self.destination = tk.StringVar(value=str(data_directory() / "runs"))
        self.search = tk.StringVar()
        self.reynolds = tk.StringVar(value="1000000")
        self.mach = tk.StringVar(value="0.0")
        self.ncrit = tk.StringVar(value="9")
        self.amin = tk.StringVar(value="-5")
        self.amax = tk.StringVar(value="15")
        self.astep = tk.StringVar(value="1")
        self.iterations = tk.StringVar(value="180")
        self.workers = tk.StringVar(value="2")
        self.catalog = ["naca0012", "naca2412", "naca4412", "naca4415"]
        self.selected = []
        self.last_dir = None
        self._build()
        self._filter()
        self.after(150,self._events)

    def _build(self):
        self.columnconfigure(0,weight=1)
        self.rowconfigure(0,weight=1)
        outer = ttk.Frame(self,padding=12)
        outer.grid(sticky="nsew")
        outer.columnconfigure(1,weight=1)
        outer.rowconfigure(1,weight=1)
        header = ttk.Frame(outer)
        header.grid(row=0,column=0,columnspan=2,sticky="ew",pady=(0,12))
        ttk.Label(header,text="AeroSuite  /  Airfoil Lab",font=("Segoe UI",18,"bold")).pack(side="left")
        ttk.Label(header,text="XFOIL • UIUC • NACA • Comparative Analysis",font=("Segoe UI",10)).pack(side="right")

        left = ttk.Frame(outer,width=330)
        left.grid(row=1,column=0,sticky="ns",padx=(0,16))
        ttk.Label(left,text="Biblioteca de perfiles",font=("Segoe UI",12,"bold")).pack(anchor="w")
        ttk.Entry(left,textvariable=self.search,width=36).pack(fill="x",pady=(6,4))
        self.search.trace_add("write",lambda *_:self._filter())
        lf=ttk.Frame(left)
        lf.pack(fill="both",expand=True)
        self.available = tk.Listbox(lf,selectmode="extended",height=14,exportselection=False)
        self.available.pack(side="left",fill="both",expand=True)
        sb=ttk.Scrollbar(lf,command=self.available.yview)
        sb.pack(side="right",fill="y")
        self.available.configure(yscrollcommand=sb.set)
        ttk.Button(left,text="Añadir selección →",command=self._add).pack(fill="x",pady=(6,2))
        ttk.Label(left,text="Perfiles para comparar (2–24):").pack(anchor="w",pady=(9,4))
        self.chosen=tk.Listbox(left,height=7,exportselection=False)
        self.chosen.pack(fill="both",expand=True)
        ttk.Button(left,text="Quitar selección",command=self._remove).pack(fill="x",pady=4)
        ttk.Button(left,text="Cargar catálogo UIUC (ZIP)",command=self.load_catalog).pack(fill="x",pady=2)
        ttk.Button(left,text="Descargar UIUC oficial",command=self._download_uiuc).pack(fill="x",pady=2)

        right=ttk.Frame(outer)
        right.grid(row=1,column=1,sticky="nsew")
        right.columnconfigure(0,weight=1)
        right.rowconfigure(3,weight=1)
        configuration=ttk.LabelFrame(right,text="Condiciones aerodinámicas",padding=10)
        configuration.grid(row=0,column=0,sticky="ew")
        params=[("Reynolds",self.reynolds),("Mach",self.mach),("Ncrit",self.ncrit),
                ("α inicial (°)",self.amin),("α final (°)",self.amax),("Paso α (°)",self.astep),
                ("Iteraciones",self.iterations),("Procesos paralelos",self.workers)]
        for i,(label,value) in enumerate(params):
            row=i//4;col=i%4
            field=ttk.Frame(configuration)
            field.grid(row=row,column=col,sticky="ew",padx=5,pady=4)
            configuration.columnconfigure(col,weight=1)
            ttk.Label(field,text=label).pack(anchor="w")
            ttk.Entry(field,textvariable=value,width=13).pack(fill="x")

        sources=ttk.LabelFrame(right,text="Motor y archivos",padding=10)
        sources.grid(row=1,column=0,sticky="ew",pady=10)
        sources.columnconfigure(1,weight=1)
        for row,label,var,selector in [
            (0,"XFOIL.exe",self.solver,self.select_solver),
            (1,"Biblioteca UIUC.zip",self.uiuc,self.select_uiuc),
            (2,"Carpeta de resultados",self.destination,self.select_output)]:
            ttk.Label(sources,text=label).grid(row=row,column=0,sticky="w",padx=(0,6),pady=3)
            ttk.Entry(sources,textvariable=var).grid(row=row,column=1,sticky="ew",pady=3)
            ttk.Button(sources,text="Examinar",command=selector).grid(row=row,column=2,padx=5)
        actions=ttk.Frame(right)
        actions.grid(row=2,column=0,sticky="ew",pady=(2,10))
        ttk.Button(actions,text="Descargar XFOIL (MIT)",command=self._download_xfoil).pack(side="left",padx=(0,10))
        self.run_button=ttk.Button(actions,text="Ejecutar análisis real",command=self.start)
        self.run_button.pack(side="left")
        ttk.Button(actions,text="Abrir resultados",command=self.open_results).pack(side="left",padx=10)

        notebook=ttk.Notebook(right)
        notebook.grid(row=3,column=0,sticky="nsew")
        self.log=tk.Text(notebook,wrap="word",height=13,font=("Consolas",9))
        notebook.add(self.log,text="Progreso y diagnósticos")
        plots=ttk.Frame(notebook,padding=8)
        notebook.add(plots,text="Gráficas")
        self.plot_list=tk.Listbox(plots,height=7,exportselection=False)
        self.plot_list.pack(side="left",fill="y")
        self.plot_list.bind("<<ListboxSelect>>",self.display_plot)
        self.preview=ttk.Label(plots,text="Ejecuta un análisis para visualizar las gráficas.")
        self.preview.pack(side="left",fill="both",expand=True,padx=10)
        self._photo=None
        self.status=ttk.Label(right,text="Preparado. Descarga XFOIL y UIUC o selecciona archivos existentes.")
        self.status.grid(row=4,column=0,sticky="ew",pady=(8,0))
        self._write("La primera ejecución requiere descargar XFOIL desde MIT. El motor no se distribuye con AeroSuite.")
        self._write("Los cálculos incompletos se marcan como parciales y quedan fuera de la clasificación.")

    def _filter(self):
        q=self.search.get().strip().lower()
        matches=[ident for ident in self.catalog if q in ident][:1000]
        self.available.delete(0,"end")
        for name in matches:self.available.insert("end",name)

    def _add(self):
        for i in self.available.curselection():
            identifier=self.available.get(i)
            if identifier not in self.selected and len(self.selected)<24:
                self.selected.append(identifier)
                self.chosen.insert("end",identifier)

    def _remove(self):
        for i in reversed(self.chosen.curselection()):
            self.selected.pop(i)
            self.chosen.delete(i)

    def _write(self,message):
        self.log.insert("end",message+"\n")
        self.log.see("end")

    def select_solver(self):
        result=filedialog.askopenfilename(title="Localizar xfoil.exe",filetypes=[("Executable","*.exe"),("Todos","*.*")])
        if result:self.solver.set(result)

    def select_uiuc(self):
        result=filedialog.askopenfilename(title="Archivo ZIP UIUC",filetypes=[("ZIP","*.zip")])
        if result:self.uiuc.set(result)

    def select_output(self):
        result=filedialog.askdirectory(title="Carpeta para resultados")
        if result:self.destination.set(result)

    def load_catalog(self):
        archive=Path(self.uiuc.get())
        try:
            if not archive.is_file():raise FileNotFoundError("Selecciona primero el ZIP oficial de UIUC")
            names=uiuc_ids(archive)
            self.catalog=sorted(set(names+["naca0012","naca2412","naca4412","naca4415"]))
            self._filter()
            self._write(f"Catálogo UIUC: {len(names)} identificadores únicos disponibles")
        except Exception as e:
            messagebox.showerror("Biblioteca UIUC",str(e))

    def _background(self,fn,done):
        if self.busy:
            messagebox.showinfo("Ocupado","Ya existe una tarea en ejecución.")
            return
        self.busy=True
        self.run_button.configure(state="disabled")
        def worker():
            try:
                result=fn()
                self.events.put(("done",done,result))
            except Exception as e:
                self.events.put(("error",str(e)))
        threading.Thread(target=worker,daemon=True).start()

    def _download_uiuc(self):
        self._write("Descargando biblioteca UIUC desde sitio oficial...")
        self._background(download_uiuc,lambda p:(self.uiuc.set(str(p)),self.load_catalog(),self._write(f"UIUC disponible en: {p}")))

    def _download_xfoil(self):
        self._write("Descargando XFOIL del MIT...")
        self._background(download_xfoil,lambda p:(self.solver.set(str(p)),self._write(f"XFOIL disponible en: {p}")))

    def start(self):
        try:
            case=XFoilCase(float(self.reynolds.get()),float(self.mach.get()),float(self.ncrit.get()),
                          float(self.amin.get()),float(self.amax.get()),float(self.astep.get()),
                          int(self.iterations.get()))
            case.validate()
            parent=Path(self.destination.get())
            uiuc=Path(self.uiuc.get())
            selected=tuple(self.selected)
            use_uiuc=any(not (s.startswith("naca") and len(s)==8 and s[4:].isdigit()) for s in selected)
            destination=parent/("analysis-"+__import__("datetime").datetime.now().strftime("%Y%m%d-%H%M%S")+"-"+uuid.uuid4().hex[:6])
            req=BatchRequest(selected,uiuc if use_uiuc else None,Path(self.solver.get()),case,
                             destination,int(self.workers.get()))
            req.validate()
        except Exception as e:
            messagebox.showerror("Configuración inválida",str(e))
            return
        self._write(f"Comenzando análisis real de {len(selected)} perfiles. Directorio: {destination}")
        def task():
            return run_batch(req,progress=lambda e:self.events.put(("progress",e["message"])))
        def finish(result):
            self.last_dir=destination
            self._write(f"Terminado: {result['status']} — {len(result['ranking_complete_only'])} perfiles en clasificación")
            self.status.configure(text=f"Resultados: {destination}")
            self.plot_list.delete(0,"end")
            for png in sorted((destination/"plots").glob("*.png")):
                self.plot_list.insert("end",png.name)
            if self.plot_list.size():
                self.plot_list.selection_set(0)
                self.display_plot()
            if result["errors"]:
                self._write("Errores: "+json.dumps(result["errors"],ensure_ascii=False))
            messagebox.showinfo("Análisis terminado","Resultados: "+str(destination)+"\nEstado: "+result["status"])
        self._background(task,finish)

    def _events(self):
        try:
            while True:
                event=self.events.get_nowait()
                if event[0]=="progress":self._write(event[1])
                elif event[0]=="error":
                    self._write("ERROR: "+event[1])
                    self.status.configure(text="Error: "+event[1][:120])
                    self.busy=False
                    self.run_button.configure(state="normal")
                    messagebox.showerror("Error de ejecución",event[1])
                elif event[0]=="done":
                    self.busy=False
                    self.run_button.configure(state="normal")
                    event[1](event[2])
        except queue.Empty:
            pass
        self.after(150,self._events)

    def display_plot(self,_event=None):
        if not self.last_dir or not self.plot_list.curselection():return
        name=self.plot_list.get(self.plot_list.curselection()[0])
        path=self.last_dir/"plots"/name
        try:
            from PIL import Image,ImageTk
            image=Image.open(path)
            image.thumbnail((710,410))
            self._photo=ImageTk.PhotoImage(image)
            self.preview.configure(image=self._photo,text="")
        except Exception as exc:
            self.preview.configure(image="",text=f"Vista previa no disponible: {exc}")

    def open_results(self):
        if self.last_dir and self.last_dir.is_dir():
            import os
            os.startfile(str(self.last_dir))
        else:
            messagebox.showinfo("Resultados","Primero ejecuta un análisis.")


def main():
    AirfoilLab().mainloop()


if __name__=="__main__":
    main()
