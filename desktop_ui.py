"""Native file picker with a queue: all Tk calls stay on the main thread."""
import datetime
import queue
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import webbrowser
from pathlib import Path


class InspectorApp:
    def __init__(self, root, scan, collect, supported, reports):
        self.root, self.scan, self.collect = root, scan, collect
        self.supported, self.reports = supported, Path(reports)
        self.events = queue.Queue()
        self.busy, self.closed, self.latest = False, False, None
        root.title('AI File Inspector')
        root.geometry('820x660')
        root.minsize(720, 600)
        root.configure(background='#f5f6f1')
        style = ttk.Style(root)
        style.theme_use('clam')
        style.configure('.', font=('Segoe UI', 11), background='#f5f6f1', foreground='#203b33')
        style.configure('TButton', padding=(18, 11), background='#e3ebe4')
        style.map('TButton', background=[('active', '#d0dfd4')])
        style.configure('Primary.TButton', background='#175f48', foreground='white')
        style.map('Primary.TButton', background=[('disabled', '#dbe3dd'), ('active', '#104a37')], foreground=[('disabled', '#53665d')])
        style.configure('Title.TLabel', font=('Segoe UI', 27, 'bold'))
        style.configure('Small.TLabel', font=('Segoe UI', 10), foreground='#4b625a')
        frame = ttk.Frame(root, padding=30)
        frame.pack(fill='both', expand=True)
        ttk.Label(frame, text='Understand your files', style='Title.TLabel').pack(anchor='w')
        ttk.Label(frame, text='Check English writing with a trained AI detector.\nGet an estimate and a report in simple English.', wraplength=650).pack(anchor='w', pady=(12,20))
        ttk.Separator(frame).pack(fill='x')
        from ai_detector import installed
        ready = 'Gradient model ready. Use at least 100 words of English prose.' if installed() else 'Local AI model missing. Restore the model folder to enable estimates.'
        ttk.Label(frame, text=ready+'\nChoose text, Word (.docx), or readable PDFs. Pictures get file checks only.\nFiles stay on your computer. Originals are never changed.', wraplength=650).pack(anchor='w', pady=20)
        choices = ttk.Frame(frame)
        choices.pack(fill='x')
        self.files_button = ttk.Button(choices, text='Choose files', style='Primary.TButton', command=self.choose_files)
        self.files_button.pack(side='left', padx=(0,12))
        self.folder_button = ttk.Button(choices, text='Choose a folder', command=self.choose_folder)
        self.folder_button.pack(side='left')
        self.status = tk.StringVar(value='Ready when you are.')
        ttk.Label(frame, textvariable=self.status, wraplength=650).pack(anchor='w', pady=(24,10))
        self.progress = ttk.Progressbar(frame, mode='indeterminate')
        self.progress.pack(fill='x')
        self.report_button = ttk.Button(frame, text='Open latest report', command=self.open_report, state='disabled')
        self.report_button.pack(anchor='w', pady=(16,18))
        ttk.Separator(frame).pack(fill='x')
        ttk.Label(frame, text='The model can be wrong. Its score is not proof of AI use.\nTechnical images stay hidden until you choose to see them.', style='Small.TLabel', wraplength=650).pack(anchor='w', pady=(16,0))
        root.protocol('WM_DELETE_WINDOW', self.close)
        self.poll_id = root.after(80, self.poll)

    def choose_files(self):
        paths = filedialog.askopenfilenames(parent=self.root, title='Choose files to check', filetypes=[('Supported files', ' '.join('*'+x for x in sorted(self.supported))), ('All files', '*.*')])
        if paths:
            self.start(paths)

    def choose_folder(self):
        path = filedialog.askdirectory(parent=self.root, title='Choose a folder to check')
        if path:
            self.start([path])

    def start(self, inputs):
        if self.busy:
            return
        self.busy = True
        self.files_button.state(['disabled'])
        self.folder_button.state(['disabled'])
        self.status.set('Finding files to check…')
        self.progress.start(12)
        events, collect, scan, reports = self.events, self.collect, self.scan, self.reports
        def worker():
            try:
                paths = collect(inputs)
                if not paths:
                    events.put(('empty', None))
                    return
                destination = reports/datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
                report = scan(paths, destination, lambda msg: events.put(('progress', msg)))
                events.put(('done', report))
            except Exception as exc:
                events.put(('error', str(exc)))
        self.worker = threading.Thread(target=worker, daemon=True)
        self.worker.start()

    def finish(self):
        self.busy = False
        self.progress.stop()
        self.files_button.state(['!disabled'])
        self.folder_button.state(['!disabled'])

    def poll(self):
        if self.closed:
            return
        while not self.events.empty():
            kind, value = self.events.get_nowait()
            if kind == 'progress':
                self.status.set(value)
            elif kind == 'done':
                self.finish()
                self.latest = Path(value)
                self.report_button.state(['!disabled'])
                self.status.set('Your report is ready. It includes any files we could not fully check.')
                self.open_report()
            elif kind == 'empty':
                self.finish()
                self.status.set('No supported files found. Choose text, pictures, Word (.docx), or PDF files.')
            elif kind == 'error':
                self.finish()
                self.status.set('The report could not be saved. You can try again.')
                messagebox.showerror('Could not finish', 'Check that the report folder is writable and has free space.\n\nDetails: '+value, parent=self.root)
        self.poll_id = self.root.after(80, self.poll)

    def open_report(self):
        if not self.latest:
            return
        if not self.latest.exists():
            self.status.set('The latest report has moved or was deleted. Check your files again to create a new one.')
            return
        try:
            opened = webbrowser.open(self.latest.resolve().as_uri())
        except Exception:
            opened = False
        if not opened:
            self.status.set('Your report is saved. Open this file in a browser: '+str(self.latest))

    def close(self):
        if self.busy and not messagebox.askyesno('Stop checking?', 'Files are still being checked. Closing now may leave an unfinished report. Close anyway?', parent=self.root):
            return
        self.closed = True
        self.root.after_cancel(self.poll_id)
        self.root.destroy()
