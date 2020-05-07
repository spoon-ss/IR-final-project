from chemdataextractor import Document



def process_json(path, size=None):
    import json
    result_dict = {}
    with open(path) as f:
        lines = f.readlines()
        size = len(lines) if size is None else size
        for (i, line) in enumerate(lines):
            if i >= size:
                break
            print("Processing " + str(i + 1) + " record out of " + str(size))
            ob = json.loads(line)
            if type(ob["authors"]) != str:
                ob["authors"] = ""
            ob['chemicals'] = _extract_chemical_from_text(ob["title"] + " " + ob["abstract"])
            ob['publish_time'] = _convert_date(ob['publish_time'])
            result_dict[str(i)] = ob
    return result_dict


def _convert_date(date_ob):
    from datetime import date
    import math
    mon_dict = {"Jan": "1", "Feb": "2", "Mar": "3", "Apr": "4", "May": "5", "Jun": "6", "Jul": "7", "Aug": "8",
                "Sep": "9", "Sept": "9", "Oct": "10", "Nov": "11", "Dec": "12"}
    date_result = date.min
    if date_ob is None:
        return date_result
    if type(date_ob) == float:
        if math.isnan(date_ob):
            return date_result
        return date.fromtimestamp(date_ob)
    if type(date_ob) == str:
        if len(date_ob) == 0 or date_ob == "NaN":
            return date_result
        date_param = [1, 1, 1]
        date_ob = date_ob.split()
        if len(date_ob) > 3:
            date_ob = date_ob[0:3]
        for i, s in enumerate(date_ob):
            if s in mon_dict:
                s = mon_dict[s]
            try:
                date_param[i] = int(s)
            except ValueError as err:
                date_param[1] = 1
        try:
            date_result = date(date_param[0], date_param[1], date_param[2])
        except ValueError:
            return date_result
    return date_result


def _extract_chemical_from_text(line: str):
    doc = Document(line)

    chem_set = set()
    for chem in doc.cems:
        chem_set.add(str(chem).lower())

    chem_list_str = ""
    for chem_str in chem_set:
        chem_list_str = chem_list_str + chem_str + " $ "
    return chem_list_str


if __name__ == '__main__':
    ob = process_json("../dataset/kaggle-covid-19-metadata/covid_comm.json")
    for key in ob:
        print(key + ": ")
        print(ob[key]['chemicals'])
        print()
