import tkinter as tk
from tkinter import messagebox
from scraper import scrape_njuskalo

def scrape():
    try:
        locations=[loc.strip() for loc in locations_input.get().split(",") if loc.strip()]
        min_price=int(min_price_input.get() or 0)
        max_price=int(max_price_input.get() or 9999)
        pages=int(pages_input.get() or 3)
    except ValueError:
        messagebox.showerror("Greška","Unos mora biti brojčani (cijene i broj stranica).")
        return

    count, filename=scrape_njuskalo(locations, min_price, max_price, pages)
    messagebox.showinfo("Gotovo",f"Spremljeno {count} oglasa u {filename}.")


root =tk.Tk()
root.title("Scraper stanova na Njuškalu")
root.geometry("400x300")

tk.Label(root, text="Lokacije: ").pack()
locations_input=tk.Entry(root, width=50)
locations_input.pack()

tk.Label(root, text="Minimalna cijena (€):").pack()
min_price_input=tk.Entry(root)
min_price_input.pack()

tk.Label(root, text="Maksimalna cijena (€):").pack()
max_price_input=tk.Entry(root)
max_price_input.pack()

tk.Label(root, text="Broj stranica za scrapeati:").pack()
pages_input=tk.Entry(root)
pages_input.pack()

tk.Button(root, text="Pokreni", command=scrape).pack(pady=10)

root.mainloop()