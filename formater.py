# replace double new line with single new line

def single_line(text):
    return text.replace("\n\n", "\n")

def read_file(file_name):
    with open(file_name, 'r') as file:
        return file.read()

if __name__ == "__main__":
    # input file name
    file_name = input("Enter the file name: ")
    text = read_file(file_name)
    print(single_line(text))