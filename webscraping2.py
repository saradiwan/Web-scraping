import requests
from bs4 import BeautifulSoup
import tkinter as tk

# Create a Tkinter window
window = tk.Tk()
window.title("Web Scraper")

# Create input field for the website URL
url_label = tk.Label(window, text="Website URL")
url_entry = tk.Entry(window)
url_label.pack()
url_entry.pack()

# Create a button that initiates the web scraping
def scrape():
    url = url_entry.get()
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    url_title = tk.Label(window, text="Scraping results for: " + url)
    url_title.pack()
    results.delete('1.0', tk.END)
    for elem in soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'a', 'li']):
        if elem.name == 'a':
            results.insert(tk.END, elem.text + ' (' + elem['href'] + ')' + '\n\n')
        else:
            results.insert(tk.END, elem.text + '\n\n')

scrape_button = tk.Button(window, text="Scrape", command=scrape)
scrape_button.pack()

# Create a text box to display the results
results_label = tk.Label(window, text="Results")
results = tk.Text(window)
results_label.pack()
results.pack()

# Run the Tkinter event loop
window.mainloop()
