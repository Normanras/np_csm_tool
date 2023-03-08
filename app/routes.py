import requests
import itertools
import pandas as pd
import re
import os
import glob
from app import app
from flask import (
    redirect,
    flash,
    request,
    render_template,
    session,
    make_response,
    url_for,
)
from werkzeug.utils import secure_filename

# Global Variables
url = "https://api.northpass.com/"

# Upload folder
UPLOAD_FOLDER = "/Users/normrasmussen/Documents/Projects/CSM_webapp/app/static/files"
# UPLOAD_FOLDER = 'static/files'
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {"csv"}


def download_csv():
    if request.method == "GET":
        download = make_response(session["dfcsv"])
        download.headers["Content-Disposition"] = "attachment; filename=export.csv"
        download.headers["Content-Type"] = "text/csv"
        return download


def key_response(response):
    if "402" in str(response):
        error = response.text
        return render_template("index.html", title="Error Home", errors=error)
    if "401" in str(response):
        error = [
            "Unauthorized access error.",
            "This can mean a lot of things,",
            "such as the key being changed.",
            "Remember, they are paired to each educator!",
        ]
        return render_template("index.html", title="Error Home", errors=error)
    return correct_key(response)


def correct_key(response):
    data = response.json()
    session["school"] = data["data"]["attributes"]["properties"]["name"]
    print(session["school"])
    return render_template("options.html", title="Options")


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/dev", methods=["GET", "POST"])
def dev_test():
    return render_template("options.html", title="Dev Test")


# DONE: Remove header for main page.
# DONE: Leave boxes but change outcome depending if file has been uploaded.


@app.route("/", methods=["GET", "POST"])
def ask_key():
    """This is the main function that asks for the API Key.
    Without this key, no other functions will work.
    It also assigns the api key to the session and clears the session upon each reload.
    """
    if session.get("key"):
        return render_template("options.html", title="Options Home")
    if request.method == "POST":
        session["key"] = request.form.get("apikey")
        # if re.search(r"\s", session["key"]):
        #    error = "Hm. That doesn't seem right"
        #    return render_template("index.html", title="Home", errors=error)
        if session["key"] is not None and len(session["key"]) > 10:
            endpoint = "/v2/properties/school"
            headers = {"accept": "application/json", "X-Api-Key": session["key"]}
            response = requests.get(url + endpoint, headers=headers)
            return key_response(response)
        error = "Hm. That doesn't seem right"
        return render_template("index.html", title="Home", error=error)

    return render_template("index.html", title="Home")


@app.route("/", methods=["GET", "POST"])
def render_home():
    if session.get("key"):
        return render_template("options.html", title="Home")
    return render_template("index.html", title="Enter Key")


@app.route("/options", methods=["GET", "POST"])
@app.route("/", methods=["GET", "POST"])
def clear_session():
    session.clear()
    return render_template("index.html", title="Home, New session")


"""
uploaded_file = request.files['file']
if  uploaded_file.filename != '':
print("File has name")
uploaded_file.save(uploaded_file.filename)
return render_template("options.html", title="Home, Now with CSV!")
"""


@app.route("/csv", methods=["GET", "POST"])
def csv():
    print("Uploading CSV")
    csvData = pd.DataFrame()
    if request.method == "POST":
        if "file" not in request.files:
            print("file not in request.files")
            flash("No file found or uploaded")
            return redirect(request.url)
        file = request.files["file"]
        if file.filename == "":
            print("no file exists")
            flash("No file found or uploaded")
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            session["file"] = filename
            file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            session["filepath"] = file_path
            file.save(file_path)
            csvData = pd.read_csv(file_path, usecols=["Email"], index_col=False)
            html_data = csvData.to_html()
            return render_template(
                "options.html", table=html_data, title="Uploaded File"
            )
        # TODO: Figure out how to delete the file after use.
    print("nothing happened")
    return render_template("options.html", title="Home, now with a CSV Table!")


@app.route("/table")
def table():
    return render_template("table.html", tables=[session["dfhtml"]], titles=["Table"])


@app.route("/bulk_add_opts", methods=["GET", "POST"])
def bulk_add_opts():
    array = []
    dict_response = {}
    dataframe = pd.DataFrame()
    count = 0

    if request.method == "POST":
        if session.get("file"):
            print("file exists! uploading data...")
            return "File Exists! Test Complete"
        else:
            while True:
                count += 1
                endpoint = f"v2/groups?page={count}"
                headers = {"accept": "application/json", "X-Api-Key": session["key"]}
                response = requests.get(url + endpoint, headers=headers)
                data = response.json()
                nextlink = data["links"]

                for response in data["data"]:
                    uuid = response["id"]
                    dict_response = {"id": uuid}
                    for keys, values in response["attributes"].items():
                        dict_response[keys] = values
                    array.append(dict_response)
                    dataframe = pd.DataFrame(array).drop(
                        "group_enrollment_link", axis=1
                    )
                print(dataframe)

                if "next" not in nextlink:
                    break

            dfgroups = dataframe.to_html()
            session["dfcsv"] = dataframe.to_csv()
            return render_template(
                "bulk_add.html", table=dfgroups, titles="Bulk Add"
            )
    else:
        return "This isn't working. Let's go our own way."


@app.route("/bulk_add_groups_opts", methods=["GET", "POST"])
def bulk_add_groups_opts():
    array = []
    dict_response = {}
    count = 0
    dataframe = pd.DataFrame()

    if request.method == "POST":
        while True:
            count += 1
            endpoint = f"v2/groups?page={count}"
            headers = {"accept": "application/json", "X-Api-Key": session["key"]}
            response = requests.get(url + endpoint, headers=headers)
            data = response.json()
            nextlink = data["links"]

            for response in data["data"]:
                uuid = response["id"]
                dict_response = {"id": uuid}
                for keys, values in response["attributes"].items():
                    dict_response[keys] = values
                array.append(dict_response)
                dataframe = pd.DataFrame(array).drop("group_enrollment_link", axis=1)
            print(dataframe)

            if "next" not in nextlink:
                break

        session["dfgroups"] = dataframe.to_html()
        session["dfcsv"] = dataframe.to_csv()
        return render_template(
            "bulk_add_groups.html", table=session["dfgroups"], titles="Bulk Add Groups"
        )
    else:
        return "This isn't working. Let's go our own way."


@app.route("/bulk_add", methods=["GET", "POST"])
def bulk_add():
    if request.method == "POST":
        emails = request.form.get("emails")
        groups = request.form.get("groups")
        if emails:
            if "\n" in emails:
                emails = emails.split("\n")
                emails = [email.strip() for email in emails]
                emails = [re.sub(r'[,]', "", email) for email in emails]
            elif "," in emails:
                emails = emails.split(",")
                emails = [email.strip() for email in emails]
            else:
                emails = []
                emails.append(emails)
        if groups:
            if "\n" in groups:
                groups = groups.split("\n")
                groups = [group.strip() for group in groups]
                groups = [re.sub(r'[,]', "", group) for group in groups]
            elif "," in groups:
                groups = groups.split(",")
                groups = [group.strip() for group in groups]
            else:
                groups = []
                groups.append(groups)

        if emails and groups:
            print(emails)
            print(groups)
            return api_add_ppl_groups(emails, groups)
        elif emails:
            return api_add_ppl(emails)
        elif groups:
            return api_add_groups(groups)

    return render_template('bulk_add.html')


#    for group in groups:
#    groupdict = {}
#    groupdict["name"] = group


def api_add_ppl(emails):
    print(emails)
    endpoint = "v2/bulk/people"
    payload = {
        "data": {
            "attributes": {"people": [{"email": emails}]}
        }
    }
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "X-Api-Key": session["key"],
    }
    response = requests.post(url + endpoint, json=payload, headers=headers)
    return check_response(response)


def api_add_groups(groups):
    print(groups)
    endpoint = "v2/bulk/people"
    payload = {
        "data": {
            "attributes": {"people": [{"groups": groups}]}
        }
    }
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "X-Api-Key": session["key"],
    }
    response = requests.post(url + endpoint, json=payload, headers=headers)
    return check_response(response)


def api_add_ppl_groups(emails, groups):
        endpoint = "v2/bulk/people"
        print(len(groups))
        combinations = list(itertools.product(emails, groups))
        print(combinations)
        payload = {
            "data": {
                "attributes": {"people": [{"email": emails, "groups": groups}]}
            }
        }
        print(payload)
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "X-Api-Key": session["key"],
        }
        response = requests.post(url + endpoint, json=payload, headers=headers)
        return check_response(response)

def check_response(response):
    response = str(response)
    if "202" in response:
        error = "Success! People have been added successfully."
        return render_template("bulk_add.html", title="People Added", error=error)
    elif "403" in response:
        error = "Uh oh. Looks like you don't have appropriate privileges."
        return render_template("bulk_add.html", error=error)
    elif "422" in response:
        error = "Hm. Looks like something was wrong with the data you added."
        return render_template("bulk_add.html", error=error)
    else:
        error = "Shrug"
        return render_template("bulk_add.html", title="Shrug", errors=error)

@app.route("/templates", methods=["GET", "POST"])
def templates():
    pass

'''
@app.route("/bulk_add_groups", methods=["GET", "POST"])
def bulk_add_groups():
    grouparr = []
    count = 0
    if request.method == "POST":
        groups = request.form.get("groups")
        if "\n" in groups:
            groups.split("\n")
            groups = [group.strip() for group in groups]
        elif "," in groups:
            groups.split(",")
            groups = [group.strip() for group in groups]
        for group in groups:
            groupdict = {}
            groupdict["name"] = group
            grouparr.append(groupdict)

        endpoint = "v2/bulk/groups"
        payload = {"data": {"attributes": {"groups": grouparr}}}
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "X-Api-Key": session["key"],
        }
        response = requests.post(url + endpoint, json=payload, headers=headers)
        print(type(response))
        response = str(response)
        if "202" in response:
            error = "Success! Groups have been added successfully."
            return render_template(
                "bulk_add_groups.html",
                table=session["dfgroups"],
                title="Groups Added",
                error=error,
            )
        elif "403" in response:
            error = [
                "Uh oh. Looks like you're not the",
                "admin or don't have appropriate privileges.",
                "Please talk to your academy admin.",
            ]
        elif "422" in response:
            error = [
                "Hm. Looks like something was wrong with the group names.",
                "Reach out to the manager of this app.",
            ]
            return render_template(
                "bulk_add_groups.html",
                table=session["dfgroups"],
                title="Groups Added",
                error=error,
            )
        else:
            error = "Shrug"
            return render_template("bulk_add_groups.html", title="Shrug", errors=error)
'''

@app.route("/bulk_courses_to_groups", methods=["GET", "POST"])
def bulk_courses_to_groups():
    pass


@app.route("/bulk_invite_ppl", methods=["GET", "POST"])
def bulk_invite_ppl():
    pass


# @app.teardown_request
# def clear_session():
#    session.clear()

app.secret_key = "@&I\x1a?\xce\x94\xbb0w\x17\xbf&Y\xa2\xc2(A\xf5\xf2\x97\xba\xeb\xfa"


if __name__ == "__main__":
    ask_key()
