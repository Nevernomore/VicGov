from tweepy import OAuthHandler
from geopy.geocoders import Nominatim
from tweepy import API
from collections import Counter
from datetime import datetime, date, time, timedelta
from geopy.exc import GeocoderTimedOut
import sys
import json
import os
import io
import re
import time
import csv
import pandas as pd
import certifi


# Helper functions to load and save intermediate steps
def save_json(variable, filename):
    with io.open(filename, "w", encoding="utf-8") as f:
        f.write(unicode(json.dumps(variable, indent=4, ensure_ascii=False)))


def load_json(filename):
    ret = None
    if os.path.exists(filename):
        try:
            with io.open(filename, "r", encoding="utf-8") as f:
                ret = json.load(f)
        except:
            pass
    return ret


def try_load_or_process(filename, processor_fn, function_arg):
    load_fn = None
    save_fn = None
    if filename.endswith("json"):
        load_fn = load_json
        save_fn = save_json
    else:
        load_fn = load_bin
        save_fn = save_bin
    if os.path.exists(filename):
        print("Loading " + filename)
        return load_fn(filename)
    else:
        ret = processor_fn(function_arg)
        print("Saving " + filename)
        save_fn(ret, filename)
        return ret


# Some helper functions to convert between different time formats and perform date calculations
def twitter_time_to_object(time_string):
    twitter_format = "%a %b %d %H:%M:%S %Y"
    match_expression = "^(.+)\s(\+[0-9][0-9][0-9][0-9])\s([0-9][0-9][0-9][0-9])$"
    match = re.search(match_expression, time_string)
    if match is not None:
        first_bit = match.group(1)
        second_bit = match.group(2)
        last_bit = match.group(3)
        new_string = first_bit + " " + last_bit
        date_object = datetime.strptime(new_string, twitter_format)
        return date_object


def time_object_to_unix(time_object):
    return int(time_object.strftime("%s"))


def twitter_time_to_unix(time_string):
    return time_object_to_unix(twitter_time_to_object(time_string))


def seconds_since_twitter_time(time_string):
    input_time_unix = int(twitter_time_to_unix(time_string))
    current_time_unix = int(get_utc_unix_time())
    return current_time_unix - input_time_unix


def get_utc_unix_time():
    dts = datetime.utcnow()
    return time.mktime(dts.timetuple())


# Get a list of follower ids for the target account
def get_follower_ids(target):
    return auth_api.followers_ids(target)


# Twitter API allows us to batch query 100 accounts at a time
# So we'll create batches of 100 follower ids and gather Twitter User objects for each batch
def get_user_objects(follower_ids):
    batch_len = 100
    num_batches = len(follower_ids) / 100
    batches = (follower_ids[i:i + batch_len] for i in range(0, len(follower_ids), batch_len))
    all_data = []
    for batch_count, batch in enumerate(batches):
        sys.stdout.write("\r")
        sys.stdout.flush()
        sys.stdout.write("Fetching batch: " + str(batch_count) + "/" + str(num_batches))
        sys.stdout.flush()
        users_list = auth_api.lookup_users(user_ids=batch)
        users_json = (map(lambda t: t._json, users_list))
        all_data += users_json
    return all_data


# Creates one week length ranges and finds items that fit into those range boundaries
def make_ranges(user_data, num_ranges=20):
    range_max = 604800 * num_ranges
    range_step = range_max / num_ranges

    # We create ranges and labels first and then iterate these when going through the whole list
    # of user data, to speed things up
    ranges = {}
    labels = {}
    for x in range(num_ranges):
        start_range = x * range_step
        end_range = x * range_step + range_step
        label = "%02d" % x + " - " + "%02d" % (x + 1) + " weeks"
        labels[label] = []
        ranges[label] = {}
        ranges[label]["start"] = start_range
        ranges[label]["end"] = end_range
    for user in user_data:
        if "created_at" in user:
            account_age = seconds_since_twitter_time(user["created_at"])
            for label, timestamps in ranges.iteritems():
                if account_age > timestamps["start"] and account_age < timestamps["end"]:
                    entry = {}
                    id_str = user["id_str"]
                    entry[id_str] = {}
                    fields = ["screen_name", "name", "created_at", "friends_count", "followers_count",
                              "favourites_count", "statuses_count"]
                    for f in fields:
                        if f in user:
                            entry[id_str][f] = user[f]
                    labels[label].append(entry)
    return labels

geo = Nominatim()

def do_geocode(address):
    try:
        return geo.geocode(address)
    except GeocoderTimedOut:
        return do_geocode(address)


if __name__ == "__main__":
    start = time.time()
    account_list = []
    if (len(sys.argv) > 1):
        account_list = sys.argv[1:]

    if len(account_list) < 1:
        print("No parameters supplied. Exiting.")
        sys.exit(0)

    consumer_key = "pboYYZ22scdz81pjym11eDZKB"
    consumer_secret = "G8pLdHKKZHfU5UsmP4MSZf2kOj4SdVpXvm0p62Yl4IkV53Wlil"
    access_token = "1104613449357643776-nVgMrh6GeLdEgkreasrNbWe2SgHhlb"
    access_token_secret = "ia6j7kTzNPhR4CaxwpI8fczRMI4GCDghfApAXgug1Zv1g"

    auth = OAuthHandler(consumer_key, consumer_secret)
    auth.set_access_token(access_token, access_token_secret)
    auth_api = API(auth)

    for target in account_list:
        print("Processing target: " + target)

        # Get a list of Twitter ids for followers of target account and save it
        filename = target + "_follower_ids.json"
        follower_ids = try_load_or_process(filename, get_follower_ids, target)

        # Fetch Twitter User objects from each Twitter id found and save the data
        filename = target + "_followers.json"
        user_objects = try_load_or_process(filename, get_user_objects, follower_ids)   #data in (target + "_followers.json")
        total_objects = len(user_objects)
        # print("Total objects is %d." % total_objects)
        gps = Nominatim()
        location_stat = []
        #print(gps.geocode('Melbourne'))  #City of Melbourne, Victoria, Australia

        # with open('output.tsv', 'wt') as out_file:
        #     tsv_writer = csv.writer(out_file, delimiter='\t')
        #     tsv_writer.writerow(['location','longitude','latitude','amount'])
        #     for user in user_objects:
        #         location = gps.geocode(user['location'],timeout=None)  #obtain the gps location for the location in user objects
        #         if user.get('location', 0) == '' or user.get('location', 0) is None or location is None:   #user has no locaiton information
        #             pass
        #         else:
        #             for stat in location_stat:
        #                 try:
        #                     if (stat['longitude'] == location.longitude) and (stat['latitude'] == location.latitude):
        #                     # if(stat['location']==location):
        #                         stat['amount'] = stat['amount'] + 1
        #                         print(stat['amount'])
        #                         break
        #                     else:
        #                         pass
        #                 except:
        #                     print("Please check the location!")
        #             location_stat.append({'location':location,'longitude':location.longitude,'latitude':location.latitude, 'amount':1})
        #             # tsv_writer.writerow([user['location'],location.longitude,location.latitude,'1'])
        #             # print ("%s,%s,%s,1" % (location,str(location.longitude),str(location.latitude)))
        #     for stat in location_stat:
        #         tsv_writer.writerow(stat)

        file = target + "_followers.csv"
        with open(file, 'wt') as out_file:
            writer = csv.writer(out_file, delimiter=',')
            writer.writerow(['location','latitude','longitude','amount'])
            for user in user_objects:
                # location = gps.geocode(user['location'],timeout=None)  # obtain the gps location for the location in user objects
                if user.get('location', 0) == '' or user.get('location', 0) is None :  # user has no locaiton information
                    pass
                else:
                    flag = False
                    for stat in location_stat:
                        try:
                            if (stat['location'] == user.get('location', 0)):
                                # if(stat['location']==location):
                                stat['amount'] = stat['amount'] + 1
                                flag = True
                                # print(stat['amount'])
                                break
                            else:
                                continue
                            location_stat.append({'location': user.get('location', 0), 'amount': 1})
                        except:
                            print("Please check the location!")

                    if flag is False:
                        location_stat.append({'location': user.get('location', 0), 'amount': 1})
                        # print(user.get('location', 0))
                    # tsv_writer.writerow([user['location'],location.longitude,location.latitude,'1'])
                    # print ("%s,%s,%s,1" % (location,str(location.longitude),str(location.latitude)))
            print(len(location_stat))
            print("*****Processing finished******")


            for stat in location_stat:
                try:
                    stat['location'] = gps.geocode(stat['location'])
                    print(stat['location'])
                except:
                    pass
            print("*******Location has converted to GPS location*******")

            # location_stat = [{'location':do_geocode(stat['location']),'amount':stat['amount']} for stat in location_stat]
            # print("*******Location has converted to GPS location*******")

            new_location_stat = []
            for item in location_stat:
                flag = False
                for new_stat in new_location_stat:
                    try:
                        if (new_stat['location'] == item['location']):
                            new_stat['amount'] = new_stat['amount'] + 1
                            # print (new_stat['amount'])
                            flag = True
                            break
                        else:
                            pass
                    except:
                        pass
                if flag is False:
                    new_location_stat.append({'location':item['location'],'amount':item['amount']})
            print("********Statistical process finished*******")

            for location in new_location_stat:
                # print(location)
                try:
                    loca= location['location']
                    writer.writerow([loca,loca.latitude,loca.longitude,location['amount']])
                except:
                    pass
            print("*******DONE********")
            # for stat in location_stat:
            #     try:
            #         location = gps.geocode(stat['location'])
            #         # tsv_writer.writerow('location': gps.geocode(stat['location']),'longitude':location.longitude,'latitude':location.latitude,'amount':stat['amount'])
            #         tsv_writer.writerow([location,location.longitude,location.latitude,stat['amount']])
            #     except:
            #         pass



        # Record a few details about each account that falls between specified age ranges
        # ranges = make_ranges(user_objects)
        # filename = target + "_ranges.json"
        # save_json(ranges, filename)

        # Print a few summaries


    end = time.time()
    print('Running time: %s Seconds' % (end - start))
