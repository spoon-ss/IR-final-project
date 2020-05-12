import json
import os

def prepocessing(path):
    """
    Get doc info from individual json file
    """
    target = list()
    # iterate through each json file in the directory
    for root, dirs, files in os.walk(path):
            for name in files:
                # extract paper id, title, authors, abstract and body from each json
                with open(os.path.join(root, name), encoding="utf-8") as f:
                    data = json.load(f)
                    text = dict()
                    text["paper_id"] = data["paper_id"]
                    text["title"] = data["metadata"]["title"]
                    name = ""
                    for author in data["metadata"]["authors"]:
                        first = author["first"]
                        if len(author["middle"]) > 0:
                            first += "." + author["middle"][-1]
                        last = author["last"]
                        if name:
                            name += ";"
                        name += first + "," + last
                    text["authors"] = name
                    if len(data["abstract"]) > 0:
                        text["abstract"] = data["abstract"][0]["text"]
                    else:
                         text["abstract"] = ""
                    body_text = ""
                    for t in data["body_text"]:
                        if body_text:
                            body_text += "\n"
                        body_text += t["text"]
                    text["body"] = body_text
                    target.append(text)

    with open('covid_comm_full_text.json', 'w') as json_file:
        for t in target:
            json_file.write(json.dumps(t)+'\n')

def get_missing_info(source_path, target_path):
    """
    Get missing info from metadata
    Source: json with info from metadata
    target: final json with complete info
    """
    # read from source json
    source = list()
    sd = dict()
    with open(source_path, 'r', encoding="utf-8") as f:
        for line in f:
            source.append(json.loads(line))
    for data in source:
        d = dict()
        paper_id =  data["paper_id"]
        d["publish_time"] = data["publish_time"]
        d["authors"] = data["authors"]
        d["title"] = data["title"]
        sd[paper_id] = d

    # get target json
    target = list()
    with open(target_path, 'r', encoding="utf-8") as f:
        for line in f:
            doc = json.loads(line)
            text = dict()
            paper_id = doc["paper_id"]
            if not paper_id or not doc["title"]:
                continue
            text["paper_id"] = doc["paper_id"]
            text["title"] = doc["title"]
            text["authors"] = doc["authors"]
            text["abstract"] = doc["abstract"]
            text["body"] = doc["body"]
            if paper_id in sd:
                text["publish_time"] = sd[paper_id]["publish_time"]
                text["authors"] = sd[paper_id]["authors"]
                text["title"] = sd[paper_id]["title"]
            else:
                text["publish_time"] = ""
            target.append(text)
    # generate final json 
    with open('covid_comm_full_text.json', 'w') as json_file:
        for t in target:
            json_file.write(json.dumps(t)+'\n')


if __name__ == '__main__':
    # path = './CORD-19-research-challenge/comm_use_subset/comm_use_subset/pdf_json/'
    # prepocessing(path)
    # get_missing_info('./covid_full.json', 'covid_comm_full.json')