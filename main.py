import requests
import re
import os
from bs4 import BeautifulSoup
from bs4.element import Comment
from md2pdf.core import md2pdf


def get_page_content_2(soup: BeautifulSoup) -> str:
    # for newer interactive pages
    text_page = ""
    # questions
    results = soup.find_all("div", class_="wq_singleQuestionCtr")
    for result in results:
        question = result.find(class_="wq_questionTextCtr").text.strip()
        choices = [choice.text.strip() for choice in result.find_all(class_="wq-answer")]

        text_page += f"{question}\n"
        for choice in choices:
            text_page += f"\t- {choice}\n"
    
    # answers
    all_text = soup.find(class_="entry-content").text
    search_result = re.search("Answers", all_text)
    if search_result:
        answers_start_pos = re.search("Answers", all_text).end()
        text_page += f"\n\nAnswers: \n"
        text_page += all_text[answers_start_pos:]
    else:
        text_page += "[FAILED TO LOCATE ANSWERS]"
    return text_page

def tag_visible(element):
    if element.parent.name in ['style', 'script', 'head', 'title', 'meta', '[document]']:
        return False
    # print("#", element, "#")
    # if element.class_ in ["wq-explanation-head-correct", "wq-explanation-head-incorrect"]:
    #     return False
    if isinstance(element, Comment):
        return False
    return True

def get_page_content(soup: BeautifulSoup) -> str:
    page = soup.find(class_="entry-content") # itemprop="text")
    texts = page.find_all(text=True)
    visible_texts = filter(tag_visible, texts)
    text = "\n".join(t.text.strip() for t in visible_texts)
    return text

def save_to_pdf(filename: str, md_page: str) -> None:
    ## add page-break before answers section
    md_page = md_page.replace("Answers:", r'<p style="page-break-before: always" ></p>Answers:')
    md_page = re.sub(r"_{3,}", "_"*12, md_page)
    md2pdf(filename, 
       md_content=md_page,
       md_file_path=None,  
       css_file_path="style/main.css", 
       base_url=None
    )

def get_page_from_url(url: str, path: str) -> str:
    ret_msg = ""

    page = requests.get(url)
    soup = BeautifulSoup(page.content, "html.parser")
    title = re.search(r"\.org\/(.+)\/$", url)[1]

    page = get_page_content(soup)
    if "Correct!" in page and "Wrong!" in page:
        # newer interative pages
        page = get_page_content_2(soup)
        ret_msg = "Parser: 2;"
    else:
        ret_msg = "Parser: 1;"

    # replace ..... -> _____
    page = re.sub(r"[….]{4,}", "_____", page)
    with open(os.path.join(path, f"{title}.md"), "w") as file:
        file.write(page)

    return ret_msg

def get_question_links(url: str, category: str) -> list:
    page = requests.get(url)
    soup = BeautifulSoup(page.content, "html.parser")
    # category = re.search(r"\.org\/category\/(.+)\/$", url)[1]
    print(category)
    print(f"Crawling [category: {category}; url: {url}]")
    path = os.path.join("raw/", category)
    if not os.path.isdir(path):
        os.mkdir(path)
    
    for a in soup.find_all("a", class_="more-link"):
        url = a["href"]
        ret_msg = get_page_from_url(url, path)

        print(f"\t - [done] {ret_msg} [{url}]")


if __name__ == '__main__':
    category = "conjunctions"
    raw_directory = f"raw/{category}"
    md_directory = f"md/{category}"
    pdf_directory = f"pdf/{category}"
    pdf_no_ans_directory = f"pdf_no_ans/{category}"
    ## 1. Crawling
    f_url_page = f"https://www.englishgrammar.org/page/{{page}}/?s=parallel"
    # url = "https://www.englishgrammar.org/category/conjunctions/"
    # f_url_page = f"https://www.englishgrammar.org/category/{category}/page/{{page}}/"
    # f_url_page = "https://www.englishgrammar.org/category/commas/page/{page}/"
    # for i in range(1, 4):
    #     print(f"on page {i}")
    #     get_question_links(
    #         f_url_page.format(page=i), 
    #         category=category
    #     )

    # ## 2. Filter out faulty pages and copy in `md`
    # for filename in os.listdir(raw_directory):
    #     raw_f = os.path.join(raw_directory, filename)
    #     md_f = os.path.join(md_directory, filename)
    #     if os.path.isfile(raw_f) and ".DS_Store" not in raw_f:
    #         with open(raw_f, "r") as i_file:
    #             md_page = i_file.read()
    #         if "Answers:" not in md_page:
    #             ## Bad quality questions to be discarded 
    #             ## (in actuality just older format that I cannot yet bother to handle) 
    #             continue
    #         ## make sure each line of answer are separated lines by markdown by appending two spaces
    #         md_page = md_page.replace(" ", " ")
    #         answers_start_pos = re.search("Answers", md_page).end()
    #         md_page = md_page[:answers_start_pos] + md_page[answers_start_pos:].replace("\n", "  \n")
    #         with open(md_f, "w") as o_file:
    #             o_file.write(md_page)
    #         print(f"[Done] {md_f}")

    # ## 3. Turn markdown pages into pdfs
    # for filename in os.listdir(md_directory):
    #     md_f = os.path.join(md_directory, filename)
    #     pdf_f = os.path.join(pdf_directory, filename).replace(".md", ".pdf")
    #     # if os.path.isfile(pdf_f):
    #     #     continue
    #     if os.path.isfile(md_f) and ".DS_Store" not in md_f:
    #         with open(md_f, "r") as i_file:
    #             md_page = i_file.read()
    #         try:
    #             save_to_pdf(pdf_f, md_page)
    #         except BaseException as e:
    #             print(f"[-] Error on {md_f}; {pdf_f}")
    #             raise e

    #         print(f"[Done] {pdf_f}")

    ## 3.5. Turn markdown pages into pdfs with no answers
    for filename in os.listdir(md_directory):
        md_f = os.path.join(md_directory, filename)
        pdf_f = os.path.join(pdf_no_ans_directory, filename).replace(".md", ".pdf")
        # if os.path.isfile(pdf_f):
        #     continue
        if os.path.isfile(md_f) and ".DS_Store" not in md_f:
            print(md_f)
            with open(md_f, "r") as i_file:
                md_page = i_file.read()
                if "Answers" in md_page:
                    md_page = md_page[:md_page.index("Answers")]
                md_page += "\n\n%s" % filename.replace(".md", "").replace("-", " ")
            try:
                save_to_pdf(pdf_f, md_page)
            except BaseException as e:
                print(f"[-] Error on {md_f}; {pdf_f}")
                raise e

            print(f"[Done] {pdf_f}")

    ## 4. some correction
    # import shutil
    # for filename in os.listdir("md/_tense"):
    #     if "tense" in filename:
    #         _f = os.path.join("md/_tense", filename)
    #         f = os.path.join("md/tense", filename)
    #         shutil.copyfile(_f, f)
    #         print(f"[Done] {f}")
    



