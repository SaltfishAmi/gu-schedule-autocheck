#!/usr/bin/python3
from selenium import webdriver
from time import sleep
import html
from bs4 import BeautifulSoup
import json
from functools import total_ordering


@total_ordering
class course_t:
  def __init__(self):
    self.id = ""
    self.number = ""
    self.section = ""
    self.name = ""
    self.crn = ""

  def to_string(self):
    return f"{self.number}-{self.section} {self.name} [{self.crn}]"

  def __lt__(self, other):
    if self.number < other.number:
      return True
    elif self.number == other.number:
      if self.section < other.section:
        return True
    return False

  def num_eq(self, other):
    return self.number == other.number and self.section == other.section

  def __eq__(self, other):
    return self.number == other.number and self.section == other.section and self.name == other.name

  def to_dict(self):
    return dict(
        id=self.id,
        number=self.number,
        section=self.section,
        name=self.name,
        crn=self.crn
    )

  @staticmethod
  def from_dict(data):
    obj = course_t()
    obj.id = data["id"]
    obj.number = data["number"]
    obj.section = data["section"]
    obj.name = data["name"]
    obj.crn = data["crn"]

    return obj


class courses_t:
  def __init__(self):
    self.items = list()

  def add(self, course):
    self.items.append(course)
    self.items.sort()

  def __eq__(self, other):
    if len(self.items) != len(other.items):
      return False
    for i in range(len(self.items)):
      if self.items[i] != other.items[i]:
        return False
    return True

  def to_json(self):
    data = list()
    for entry in self.items:
      data.append(entry.to_dict())
    return json.dumps(data)

  @staticmethod
  def from_json(str):
    result = courses_t()
    data = json.loads(str)
    for entry in data:
      result.add(course_t.from_dict(entry))
    return result


@total_ordering
class diff_t:
  def __init__(self):
    self.type = ""
    self.entry = course_t()

  def to_string(self):
    return f"{self.type} {self.entry.to_string()}"

  def __lt__(self, other):
    if self.entry < other.entry:
      return True
    elif self.entry.num_eq(other.entry):
      return True if self.type == "-" else False


class diffs_t:
  def __init__(self):
    self.items = list()

  def add(self, type, data):
    for entry in data:
      # entry is of type course_t
      item = diff_t()
      item.type = type
      item.entry = entry
      self.items.append(item)
    self.items.sort()

  def to_string(self):
    result = ""
    for entry in self.items:
      result += entry.to_string() + "\n"
    return result


def diff(old, new):
  minuses = old.items.copy()
  for i in range(len(new.items)):
    try:
      minuses.remove(new.items[i])
    except ValueError:
      pass
  pluses = new.items.copy()
  for i in range(len(old.items)):
    try:
      pluses.remove(old.items[i])
    except ValueError:
      pass
  result = diffs_t()
  result.add("-", minuses)
  result.add("+", pluses)
  return result


def post(driver, path, params):
  driver.execute_script("""
  function post(path, params, method='post') {
    const form = document.createElement('form');
    form.method = method;
    form.action = path;
  
    for (const key in params) {
      if (params.hasOwnProperty(key)) {
        const hiddenField = document.createElement('input');
        hiddenField.type = 'hidden';
        hiddenField.name = key;
        hiddenField.value = params[key];
  
        form.appendChild(hiddenField);
      }
    }
  
    document.body.appendChild(form);
    form.submit();
  }
  
  post(arguments[1], arguments[0]);
  """, params, path)


def refresh():
  initURL = "https://bn-reg.uis.georgetown.edu/StudentRegistrationSsb/ssb/term/termSelection?mode=search"
  postURL = "https://bn-reg.uis.georgetown.edu/StudentRegistrationSsb/ssb/term/search?mode=search"
  postReq = {"term": "202330", "studyPath": "",
             "studyPathText": "", "startDatepicker": "", "endDatepicker": ""}
  jsonURL = "https://bn-reg.uis.georgetown.edu/StudentRegistrationSsb/ssb/searchResults/searchResults?txt_subject=COSC&txt_course_number_range=4000&txt_course_number_range_to=6999&txt_term=202330"

  fireFoxOptions = webdriver.FirefoxOptions()
  fireFoxOptions.add_argument("-headless")
  browser = webdriver.Firefox(options=fireFoxOptions)

  browser.get(initURL)

  session_id = browser.execute_script(
      "return window.sessionStorage['xe.unique.session.storage.id'];")
  postReq["uniqueSessionId"] = session_id
  jsonURL += "&uniqueSessionId=" + session_id

  sleep(1)
  post(browser, postURL, postReq)

  sleep(1)
  browser.get(jsonURL)

  parser = BeautifulSoup(browser.page_source, features="html.parser")
  json_data = html.unescape(parser.find('div', attrs={'id': 'json'}).text)
  
  browser.quit()

  data = json.loads(json_data)

  courses = courses_t()

  for entry in data["data"]:
    course = course_t()
    course.id = entry["id"]
    course.number = entry["courseNumber"]
    course.section = entry["sequenceNumber"]
    course.name = entry["courseTitle"].strip()
    course.crn = entry["courseReferenceNumber"]
    if course.number.startswith("4") and course.section != "02":
      continue
    courses.add(course)

  return courses


def test():
  f = open("courses.list", "r")
  old_courses = courses_t.from_json(f.read())
  f.close()
  new_courses = refresh()
  if not new_courses == old_courses:
    alert(diff(old_courses, new_courses))
    f = open("courses.list", "w")
    f.write(new_courses.to_json())
    f.close()


def init():
  new_courses = refresh()
  f = open("courses.list", "w")
  f.write(new_courses.to_json())
  f.close()


def alert(content):
  # user defined
  pass

while True:
  test()
  sleep(28800)
