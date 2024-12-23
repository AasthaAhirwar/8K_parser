import re
import requests
from bs4 import BeautifulSoup as bs
import pandas as pd
import time

file_with_links = pd.read_csv('merged_txt_files.csv')


class Start_Info:
    def __init__(self, name, reg):
        self.name = name
        self.reg = reg
        self.value = None


def get_text(link):
    page = requests.get(link, headers={'User-Agent': 'sample@sample.com'})
    html = bs(page.content, "lxml")
    return html.get_text("\n").replace(u'\xa0', ' ').replace("\t", " ").replace("\x92", "'").replace("\u2009", " ").split("\n")

def main():

    corporate_events = ["Other Events", "Entry [Ii]nto a Material Definitive Agreement"]

    item_pattern = re.compile("|".join(["^(Item [1-9][\.\d]+.*" + s + ")" for s in corporate_events]))
    general_item_pattern = re.compile("^(Item [1-9][\.\d]+)")
    maybe_pattern = re.compile("|".join(corporate_events))
    stop_pattern = re.compile("SIGNATURE", re.IGNORECASE)

    final_info = pd.DataFrame(columns=['company_cik', 'company_name', 'Events'])

    for link in file_with_links['submission_file_link']:
        time.sleep(3)
        #link = "https://www.sec.gov/Archives/edgar/data/1320414/000110465924075765/0001104659-24-075765.txt"
        print(link)

        text = get_text(link)

        text_iter = iter(text)

        start_info = [
            Start_Info("company_cik", re.compile("(CENTRAL INDEX KEY:)([\s\d]+)", re.IGNORECASE)),
            Start_Info("company_name", re.compile("(COMPANY CONFORMED NAME:)(.+)", re.IGNORECASE)),
        ]

        for line in text_iter:
            for c in start_info:
                if c.value is None and c.reg.search(line) is not None:
                    c.value = c.reg.search(line).group(2).strip()
                    break

            if all([c.value is not None for c in start_info]):
                break

        data = list()
        batch = list()
        to_append = False
        maybe_valid = False

        for line in filter(lambda x: x.strip() != "", text_iter):
            if item_pattern.search(line) is not None:
                to_append = True

                if batch:
                    data.append("\n".join(batch))
                    batch.clear()
                
                batch.append(line)

            elif general_item_pattern.search(line) is not None:
                to_append = False
                maybe_valid = True

                if batch:
                    data.append("\n".join(batch))
                    batch.clear()

                batch.append(line)

            elif stop_pattern.search(line) is not None:
                if batch:
                    data.append("\n".join(batch))
                    batch.clear()
                break

            elif to_append:
                batch.append(line)

            elif maybe_valid:
                if maybe_pattern.search(line) is not None:
                    batch.append(line)
                    to_append = True
                else:
                    batch.clear()

                maybe_valid = False

        print("\n".join(["{}: {}".format(c.name, c.value) for c in start_info]))
        # print("\n".join([d for d in data]))

        df = pd.DataFrame(data, columns=['Events'])

        for c in start_info:
            df[c.name] = c.value

        df = df[[c.name for c in start_info] + ["Events"]]

        #if df['Events'] is not None:
        final_info = pd.concat([final_info, df], ignore_index=True)
        print(final_info)
    final_info.to_csv('training_data.csv')


if __name__ == "__main__":
    main()