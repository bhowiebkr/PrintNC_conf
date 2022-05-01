from collections import OrderedDict
import re


class LinuxCNCConfig(object):
    def __init__(self, path):

        self.data = OrderedDict()
        if path:
            self.read(path)

    def read(self, path):
        lines = None

        # read the file
        with open(path, "r") as f:
            lines = f.readlines()
        if not lines:
            return

        curr_section = None

        comment_buffer = []

        # Read every line
        for line in lines:
            line = line.rstrip()

            # ignore spaces and comments
            if not line:
                continue

            if line.startswith("#"):
                # Skip annoying pnccnof line comments
                if re.match("^#\*+$", line):
                    continue

                c = line[1:]
                c = c.strip()
                print([c])
                comment_buffer.append(c)
                continue

            # Make a new section if it starts with "["
            if line.startswith("["):
                self.data[line] = {"comments": comment_buffer, "variables": []}
                comment_buffer = []
                curr_section = line
                continue

            # Any other line starting with a letter is a key for the current section
            if re.search("^[a-zA-Z]", line) is not None:
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip()
                self.data[curr_section]["variables"].append([key, val, comment_buffer])
                comment_buffer = []
                continue

    def write(self, save_path):
        lines = []

        # Loop over each section
        for section, data in self.data.items():

            comments = data["comments"]
            keys = data["variables"]

            if comments:
                lines.append("\n")
                for comment in comments:
                    lines.append(f"# {comment}\n")

            # append the section if it isn't empty
            if len(keys):
                lines.append(f"\n{section}\n")

            # append the key, values, comments
            for key, val, comments in keys:
                if comments:
                    lines.append("\n")
                    for comment in comments:
                        lines.append(f"# {comment}\n")

                lines.append(f"{key} = {val}\n")

        # remove the newline on the first line
        lines[0] = lines[0][2:]

        with open(save_path, "w") as f:
            f.writelines(lines)
