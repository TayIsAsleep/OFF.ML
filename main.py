from flask import Flask
from flask import render_template
from flask import jsonify
from flask import redirect
from flask import request
import os

# API
def base_encode(value_input, alphabet="0123456789"):
    if value_input == 0:return alphabet[0]
    if value_input < 0:return -1
    arr = []
    arr_append = arr.append  # Extract bound-method for faster access.
    _divmod = divmod  # Access to locals is faster.
    base = len(alphabet)
    while value_input:
        value_input, rem = _divmod(value_input, base)
        arr_append(alphabet[rem])
    arr.reverse()
    return ''.join(arr)
def base_decode(value_input, alphabet="0123456789"):
    if type(value_input) == str:
        for character in value_input:
            if character in alphabet:continue
            value_input = value_input.replace(character, alphabet[0])

    base = len(alphabet)
    strlen = len(value_input)
    num = 0

    idx = 0
    for char in value_input:
        power = (strlen - (idx + 1))
        num += alphabet.index(char) * (base ** power)
        idx += 1

    return num

def load_chp(chp_name):
    if not chp_name.endswith(".chp"):chp_name+=".chp"
    with open(chp_name,"r") as f:
        lines = [x.strip("\n") for x in f.readlines()]
    
    chp_data = ""
    chp_header = {}
    mode = None
    for line in lines:
        try:
            if line == "":continue

            if line[0] + line[-1] == "[]":
                mode = line[1:-1]
                continue

            if mode == "header":
                key, value = line.split(" = ")
                chp_header[key] = value
                continue
            
            if mode == "characters":
                chp_data += line
                continue
            
            if mode == "emojis":
                chp_data += eval(f"'\\U000{line}'")
                continue

            if mode == "endchp":
                break
        except:
            continue
    
    return {
        "data":chp_data,
        "header":chp_header
    }

def key_to_emoji(input_value):
    if type(input_value) == int:
        input_value = [input_value]
    return "".join(base_encode(x, alphabet=emojis) for x in input_value)
def emoji_to_key(input_value):
    if type(input_value) != list:
        input_value = list(input_value)

    to_return = []
    for x in input_value:
        if x in emojis:
            to_return.append(emojis.index(x))
    return to_return

def database_read():
    with open("data.txt", "r", encoding="utf-8") as f:
        lines = f.readlines()

        data = {}
        for line in lines:
            key, value = line.strip().split(" = ")
            data[key] = value
        
        return data
def database_write(key, value):
    """
        `key` must be list.
    """

    if r := check_key_availability(key) != 0:return r

    key = ','.join(str(x) for x in key)

    with open("data.txt", "a", encoding="utf-8") as f:
        f.write(f"{key} = {value}\n")
    
    return 0

def check_key_availability(input_value):
    """
        `input_value` must be list.

        0 == `not found in database` (OK)

        -1 == `found in database` (NOT AVAILABLE)
    """

    input_value = ','.join(str(x) for x in input_value)
    
    if input_value in database_read():
        return -1
        
    return 0
def get_shortest_available_key():
    data = database_read()

    i = 0
    while 1:
        new_key = key_to_emoji(i)
        
        if not ",".join(str(x) for x in emoji_to_key(new_key)) in data:
            break
        
        i += 1

    return emoji_to_key(new_key)

def check_if_key_legal(key):
    """
        This takes the EMOJI KEY, not the numbers
    """
    for c in str(key):
        if not c in emojis:
            return -1, c
    return 0, None

if __name__ == "__main__":
    if not os.path.isfile("data.txt"):a=open("data.txt","w");a.close()

    emojis = load_chp("base")["data"] # Import emojis

    app = Flask(__name__)

    # Short URL redirect
    @app.route("/<key>")
    def short_links(key):
        try:
            return redirect(database_read()[",".join(str(x) for x in emoji_to_key(key))])
        except:
            return redirect("/shorten?showError=1")
    

    # User landing pages
    @app.route("/shorten")
    def index():
        return render_template("index.html")


    # API routes
    @app.route("/API/fetch_empty_key")
    def API_fetch_empty_key():
        key = key_to_emoji(get_shortest_available_key())
        print(key)
        return str(key)
    
    @app.route("/API/check_key_availability/<key>")
    def API_check_key_availability(key):
        key = emoji_to_key(key)
        return jsonify(check_key_availability(key))
    
    @app.route("/API/claim_key")
    def API_claim_key():
        my_response = {
            "status": "ERROR",
            "code": -1,
            "message": "Something must have gone wrong, because nothing was returned!"
        }
        
        key = request.args["key"]
        value = request.args["value"]

        c = check_if_key_legal(key)
        if c[0] != 0:
            if c[0]== -1:
                my_response["code"] = -3
                my_response["status"] = "BAD"
                my_response["message"] = f'Key has illegal character/characters (Found "{c[1]}")'
        else:
            key = emoji_to_key(key)

            if check_key_availability(key) == 0:
                database_write(key,value)
                my_response["code"] = 0
                my_response["status"] = "OK"
                my_response["message"] = {
                    "key":key,
                    "key_emoji":key_to_emoji(key)
                }
            else:
                my_response["code"] = -2
                my_response["status"] = "BAD"
                my_response["message"] = "Key is not available"
        
        return jsonify(my_response)

    @app.route("/API/read_key/<key>")
    def API_read_key(key):
        my_response = {
            "status": "ERROR",
            "code": -1,
            "message": "Something must have gone wrong, because nothing was returned!",
            "data":None
        }

        key = ",".join(str(x) for x in emoji_to_key(key))

        data = database_read()

        if key in data:
            my_response["code"] = 0
            my_response["status"] = "OK"
            my_response["message"] = f"Key existed. Here is the data"
            my_response["data"] = data[key]
        else:
            my_response["code"] = -2
            my_response["status"] = "BAD"
            my_response["message"] = "Key does not exist on server"

        return jsonify(my_response)       


    # Debug routes
    @app.route("/decode/<key>")
    def path_decode(key):
        print(key)
        return str(emoji_to_key(key))
    
    @app.route("/encode/<key>")
    def path_encode(key):
        print(key)
        emoji_thing = key_to_emoji(int(x) for x in key.split(","))
        new_key = emoji_to_key(emoji_thing)
        return str(f"<pre>{emoji_thing}</pre><pre>{','.join(str(x) for x in new_key)}</pre>")

    app.run(use_reloader=False)
