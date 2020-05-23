import requests
from bs4 import BeautifulSoup as bs
import re

import datetime
import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

"""WEB SCRAPING"""
homework_data = {}
class_names = []
class_days = {}
debug = True

# source env/bin/activate

def getHomework():
    global homework_data, class_names, class_days
    try:
        num_of_courses = input('How many courses are you taking?') # for getting class links
        if (len(num_of_courses) == 0):
            num_of_courses = 7
    except:
        print("Enter a number")

    password = input('Enter your password')
    if (len(password) == 0):
        password = 'Nope'

    login = {
        'username': 'Aditya.Pawar',
        'password': password,
        'anchor': '',
        'logintoken': ''
    }

    homework_data = {}

    """Make a session to login and get info"""
    with requests.Session() as s:
        url = 'https://learn.vcs.net/login/index.php'
        res = s.get(url)
        soup = bs(res.content, 'html.parser')
        login['logintoken'] = soup.find('input', attrs={'name': 'logintoken'})['value']
        """Save the login token and sign in"""
        # print(login['logintoken'])

        """Get the website data"""
        res = s.post(url, data=login)
        soup = bs(res.content, 'html.parser')
        if len(soup.find_all('div', attrs={'class':'loginerrors'})) != 0: # check if login was valid
            print('Invalid Login')
        else:
            print('Logged in')

        classes = soup.find_all('div', attrs={'class': 'column c1'}) # get links on menu bar
    #[print("{} \n".format(c)) for c in classes[3:num_of_courses + 3]]

    class_names = [] # used to later ask the user what day they have the courses on

    classes = classes[3:num_of_courses + 3] # get all classes
    for class_ in classes:
        href = class_.find('a') # find the class link
        link = href['href']

        class_name = href['title']
        class_names.append(class_name) # add to class names
        print(class_name)


        r = s.get(link) # class page home
        soup = bs(r.content, 'html.parser')
        lesson_plans_page = soup.find('a', attrs={'title': 'Lesson Plans and Homework'}) # find lesson plans and homework link
        plans = lesson_plans_page['href'] # go to the lesson plan page

        r = s.get(plans)
        soup = bs(r.content, 'html.parser')
        lesson_plans_ = soup.find_all('div', attrs={'class': 'activityinstance'}) # find all links if multiple quarters
        homework_dict_temp = {}

        for lesson_plans in lesson_plans_: # for different quarters
            print(lesson_plans.find('a').text)
            lessons = lesson_plans.find('a') # find the lesson
            lessons_link = lessons['href']


            r = s.get(lessons_link)
            soup = bs(r.content, 'html.parser')
            possible_lessons = soup.find_all('li', attrs={'class':'notselected'}) # each lesson plan for a single day
            lesson = soup.find('li', attrs={'class':'selected'}) # same as above
            possible_lessons.append(lesson)



            #print(possible_lessons)

            for lesson in possible_lessons: # loop through all lessons
                #print(lesson)
                try:
                    lesson_link = lesson.find('a')['href']
                    date = lesson.find('a').text
                    if debug:
                        print('Getting Data: ' + date)
                    # print(lesson_link)
                    # print('\n')
                except:
                    if debug:
                        print('No Data Found') # Error on lesson links



                r = s.get(lesson_link)
                t = r.content.decode("utf-8")
                soup = bs(t, 'html.parser')


                """Get homeowork"""
                main = soup.find('div', attrs={'role':'main'})
                contents = main.find('div', attrs={'class':'box contents'})

                if 'Homework' in str(contents):
                    # find the text 'homework' on page
                    hw = contents.find('h3', text=re.compile('Homework'))
                    hw_contents = bs(str(contents).split(str(hw))[-1], 'html.parser') # contents of homework

                    homework = hw_contents.find('ul')
                    try:
                        str(homework.text)
                        homework_dict_temp.__setitem__(date, homework.text) # set the homeowrk of that date to the homework contents
                    except:
                        print('No Homework found on {}\n'.format(lesson_link))
                else:
                    print('No homework found on {}\n'.format(lesson_link))


            print('\n\n')
            homework_data.__setitem__(class_name, homework_dict_temp)

    if debug:
        print(homework_data)
        pass
    """Checks where to put homwork on calendar"""
    for class_name in class_names:
        while True:
            inp = input('What day do you have {}? (A or B)'.format(class_name)).upper()
            if inp == 'A' or inp == 'B':
                break
            else:
                print('Please enter either \'A\' or \'B\'')

        class_days.__setitem__(class_name, inp)





"""GOOGLE CALENDAR API"""
# adds event to google calendar
def addEvent(summary=None, location=None, description=None, notifications=False, startDateTime=None, endDateTime=None, timeZone=None):
    if startDateTime == None or endDateTime == None or timeZone == None:
        print('Error creating event: Invalid Values')
        return {}
    else:
        try:
            event = {
              'summary': summary,
              'location': location,
              'description': description,
              'start': {
                'dateTime': startDateTime,
                'timeZone': timeZone,
              },
              'end': {
                'dateTime': endDateTime,
                'timeZone': timeZone,
              },
              'reminders': {
                'useDefault': notifications,
              },
            }

            event = service.events().insert(calendarId='primary', body=event).execute()
            print('Event created: {}'.format((event.get('htmlLink'))))
        except:
            print('ERROR ADDING EVENT, CHECK DATE PARSER')

# If modifying these scopes, delete the file token.pickle.
# To clear calendar, use: https://developers.google.com/calendar/v3/reference/calendars/clear?apix_params=%7B%22calendarId%22%3A%22primary%22%7D
SCOPES = ['https://www.googleapis.com/auth/calendar']
service = None

def google_cal_init():
    global service
    """Shows basic usage of the Google Calendar API.
    Prints the start and name of the next 10 events on the user's calendar.
    """
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = build('calendar', 'v3', credentials=creds)

    # Call the Calendar API
    # service.calendars().clear('primary').execute()

    # event = addEvent(summary='Test', description='Testing the googleCal API',
    #                     startDateTime='2019-12-29T15:00:00', endDateTime='2019-12-29T15:00:00',
    #                     timeZone='America/Los_Angeles')

def parse_dict(dictionary):
    for classname, data in dictionary.items():
        print(classname)
        for date, hw in data.items():

            addEvent(summary=classname, description=hw,
            startDateTime=parse_date(date, class_days[classname])[0],
            endDateTime=parse_date(date, class_days[classname])[-1],
            timeZone='America/Los_Angeles')




def parse_date(date, day):
    try:
        # parse the data in the homwork_data dict
        index = 0 if day == 'A' else -1
        if 'January' in date:
            month = 1
            year = 2020
            day = date.split('January ')[-1].split('/')[index] if len(date.split('January ')[-1]) <= 5 else date.split('January ')[-1][:5].split('/')[index]
        elif 'February' in date:
            month = 2
            year = 2020
            day = date.split('February ')[-1].split('/')[index] if len(date.split('February ')[-1]) <= 5 else date.split('February ')[-1][:5].split('/')[index]
        elif 'March' in date:
            month = 3
            year = 2020
            day = date.split('March ')[-1].split('/')[index] if len(date.split('March ')[-1]) <= 5 else date.split('March ')[-1][:5].split('/')[index]
        elif 'April' in date:
            month = 4
            year = 2020
            day = date.split('April ')[-1].split('/')[index] if len(date.split('April ')[-1]) <= 5 else date.split('April ')[-1][:5].split('/')[index]
        elif 'May' in date:
            month = 5
            year = 2020
            day = date.split('May ')[-1].split('/')[index] if len(date.split('May ')[-1]) <= 5 else date.split('May ')[-1][:5].split('/')[index]
        elif 'June' in date:
            month = 6
            year = 2020
            day = date.split('June ')[-1].split('/')[index] if len(date.split('June ')[-1]) <= 5 else date.split('June ')[-1][:5].split('/')[index]
        elif 'July' in date:
            month = 7
            year = 2019
            day = date.split('July ')[-1].split('/')[index] if len(date.split('July ')[-1]) <= 5 else date.split('July ')[-1][:5].split('/')[index]
        elif 'August' in date:
            month = 8
            year = 2019
            day = date.split('August ')[-1].split('/')[index] if len(date.split('August ')[-1]) <= 5 else date.split('August ')[-1][:5].split('/')[index]
        elif 'September' in date:
            month = 9
            year = 2019
            day = date.split('September ')[-1].split('/')[index] if len(date.split('September ')[-1]) <= 5 else date.split('September ')[-1][:5].split('/')[index]
        elif 'October' in date:
            month = 10
            year = 2019
            day = date.split('October ')[-1].split('/')[index] if len(date.split('October ')[-1]) <= 5 else date.split('October ')[-1][:5].split('/')[index]
        elif 'November' in date:
            month = 11
            year = 2019
            day = date.split('November ')[-1].split('/')[index] if len(date.split('November ')[-1]) <= 5 else date.split('November ')[-1][:5].split('/')[index]
        elif 'December' in date:
            month = 12
            year = 2019
            day = date.split('December ')[-1].split('/')[index] if len(date.split('December ')[-1]) <= 5 else date.split('December ')[-1][:5].split('/')[index]
        else:
            month = -1
            year = -1
            day = -1
                # start time                                                            # end time
        return ('{}-{}-{}T15:00:00'.format(year, month, day.replace(',', '').strip()), '{}-{}-{}T16:00:00'.format(year, month, day.replace(',', '').strip()))# .strip(' , 2019 2018')

    except:
        print('Error on {} date'.format(date))
        print('Day: {}'.format(day))

        return 'DATE PARSING ERROR'





def main():
    getHomework()
    # google_cal_init()
    # parse_dict(homework_data)


if __name__ == '__main__':
    main()
