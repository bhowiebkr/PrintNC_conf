import json
import os
import re

DEBUG = True


class LinuxCNCDocs(object):
    def __init__(self):
        self.data = None
        doc_file_path = os.path.join(os.path.dirname(__file__), "docs.json")
        with open(doc_file_path, "r") as f:
            self.data = json.load(f)

    def get_section_doc(self, section):
        try:
            docs = self.data[section]["description"]
            return docs
        except KeyError as e:
            if DEBUG:
                print("error:", e)

    def get_variable_docs(self, section, variable):
        print("get_variable_docs")
        print("section:", section, "variable:", variable)
        try:
            docs = self.data[section]["variables"][variable]
            docs = f"<b>{variable}</b><br>{docs}"
            docs = re.sub(r"([a-z])\. ", r"\g<1>.<br><br>", docs)
            return docs
        except KeyError as e:
            if DEBUG:
                print("error:", e)
