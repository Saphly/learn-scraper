import config
import tkinter as tk
from tkinter import messagebox
import scraper
import requests

def username_cons(input):
    username.set(username.get().lower())
    if len(username.get()) > 8:
        messagebox.showerror("Error", "Username is too long")
        username.set(username.get()[:8])

def close_app():
    window.destroy()

def run_app():
    pass

window = tk.Tk()

window.title("Learn Scraper")
window.resizable(width="false", height="false")

frame_header = tk.Frame(window)
centre_frame = tk.Frame(window, borderwidth=2, pady=5)
bottom_frame = tk.Frame(window, borderwidth=2, pady=5)
frame_header.grid(row=0, column=0)
centre_frame.grid(row=1, column=0)
bottom_frame.grid(row=2, column=0)

header = tk.Label(frame_header, text = "LEARN SCRAPER TOOL", bg='pink', fg='white', height='3', width='50', font=("Helvetica 16 bold"))
header.grid(row=0, column=0)

frame_username = tk.Frame(centre_frame, borderwidth=2,relief="sunken")
frame_pw = tk.Frame(centre_frame, borderwidth=2, relief="sunken")
frame_list = tk.Listbox(centre_frame, borderwidth=2, selectmode="single", relief='sunken')

input_username = tk.Label(frame_username, text="Username: ")
input_pw = tk.Label(frame_pw, text="Password: ")
for x in range(100):
    frame_list.insert('end', str(x))

scrollbar = tk.Scrollbar(frame_list, orient="vertical")
scrollbar.config(command=frame_list.yview)
scrollbar.pack(side="right", fill="y")

frame_list.config(yscrollcommand=scrollbar.set)

username = tk.StringVar()
pw = tk.StringVar()

username_entry = tk.Entry(frame_username, textvariable=username)
username_entry.bind("<KeyRelease>", username_cons)
pw_entry = tk.Entry(frame_pw, textvariable=pw, show='*')

frame_username.pack(fill='x', pady=2)
frame_pw.pack(fill='x', pady=2)
frame_list.pack(fill='x', pady=2)

input_username.pack(side='left')
username_entry.pack(side='left')
input_pw.pack(side='left')
pw_entry.pack(side='left', padx=4)

button_start = tk.Button(bottom_frame, text='Enter', command = run_app, fg='dark green', relief='raised', width=10, font=('Helvetica 9 bold'))
button_start.grid(column=0, row=0, sticky='w', padx=50, pady=2)

button_end = tk.Button(bottom_frame, text='Exit', command = close_app, fg='dark red', relief='raised', width=10, font=('Helvetica 9 bold'))
button_end.grid(column=1, row=0, sticky='e', padx=50, pady=2)




window.mainloop()