#!/usr/bin/env python3

import json
import os
import re
import sys
import unicodedata
from pathlib import Path

import geojson

WORKDIR = Path("/tmp/places_workdir")
GEONAMES_DIR = WORKDIR / "geonames"
GEOJSON_DIR = WORKDIR / "geojson"

NATION_FILE = "cb_2015_us_nation_5m.json"
STATES_FILE = "cb_2015_us_state_500k.json"
COUNTIES_FILE = "cb_2015_us_county_500k.json"
ZIPCODES_FILE = "cb_2015_us_zcta510_500k.json"

# This data structure fills in blanks observed in Geonames data.
EXTRA_ZIP_CODE_INFO = {
    "17270": ("Williamson", "PA"),
    "17767": ("Salona", "PA"),
    "19542": ("Monocacy Station", "PA"),
    "20307": ("Washington", "DC"),
    "42084": ("Tolu", "KY"),
    "42731": ("Dubre", "KY"),
    "45145": ("Marathon", "OH"),
    "45418": ("Trotwood", "OH"),
    "48921": ("Lansing", "MI"),
    "56177": ("Trosky", "MN"),
    "64192": ("Kansas City", "MO"),
    "66019": ("Clearview City", "KS"),
    "84144": ("Salt Lake City", "UT"),
    "95250": ("Mountain Ranch", "CA"),
    "95314": ("Dardanelle", "CA"),
    "98205": ("Everett", "WA"),
    "98929": ("Goose Prairie", "WA"),
}


def ascii_alias(s):
    """
    If this name contains combining characters, return the version without combining characters for use as an alias.
    """
    if not s:
        return None

    try:
        ascii = s.encode("ascii")
        return None
    except Exception:
        pass

    alias = ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')

    if alias == s:
        return None
    return alias


def features(filename):
    path = os.path.join(GEOJSON_DIR, filename)
    collection = geojson.load(open(path))
    for feature in collection.features:
        yield feature


class Place:

    def __init__(self, place_type, geography, place_id, name, abbreviated_name=None, parent=None):
        """Rationalizes geographic data from multiple scales into a single format."""
        self.type = place_type
        self.geography = geography
        self.id = place_id
        self.name = name
        self.abbreviated_name = abbreviated_name
        self.parent = parent
        self.aliases = set()

        # If the name or its abbreviation contains diacritics, create an ASCII version to serve as an alias.
        aliases = map(ascii_alias, [self.name, self.abbreviated_name])
        for x in aliases:
            if x:
                self.aliases.add(x)

    @property
    def output(self):
        """A Place is output as two lines: one containing metadata and one containing a GeoJSON object."""
        return "\n".join([json.dumps(self.jsonable), json.dumps(self.geography)])

    @property
    def jsonable(self):
        data = {"type": self.type, "id": self.id, "name": self.name}
        if self.abbreviated_name:
            data['abbreviated_name'] = self.abbreviated_name

        if self.aliases:
            aliases = []
            data['aliases'] = aliases
            for alias in self.aliases:
                aliases.append({"name": alias, "language": 'eng'})

        if self.parent:
            data['parent_id'] = self.parent.id
        else:
            data['parent_id'] = None

        return data

    def __str__(self):
        data = self.jsonable
        return json.dumps(data)


class Nation(Place):

    @classmethod
    def from_filename(cls, filename):
        [nation] = list(features(filename))
        props = nation.properties
        nation = cls(
            'nation', nation.geometry, props['GEOID'], props['NAME'],
            abbreviated_name=props['GEOID']
        )
        nation.seen_names = set()
        return nation


class State(Place):

    def __init__(self, *args, **kwargs):
        super(State, self).__init__(*args, **kwargs)
        self.seen_names = set()

    def saw_place_name(self, name):
        """
        Record that we saw a record of a place name in this state. This will let us ensure that we 
        will not alias a ZIP code to a place name if the place name is already associated with a
        census designated place.
        """
        self.seen_names.add(name)


class States(object):

    @classmethod
    def from_filename(cls, filename, nation):
        states = cls()
        for state in features(filename):
            props = state.properties
            place = State('state', state.geometry, place_id=props['STATEFP'], name=props['NAME'],
                          abbreviated_name=props['STUSPS'], parent=nation)
            states.add(place)
        return states

    def __init__(self):
        self.by_abbreviation = {}
        self.by_id = {}

    def add(self, state):
        self.by_abbreviation[state.abbreviated_name] = state
        self.by_id[state.id] = state


class Counties:

    @classmethod
    def from_filename(cls, filename, states):
        counties = []
        for county in features(filename):
            state = states.by_id[county.properties['STATEFP']]
            props = county.properties
            name = props['NAME']
            place = Place(
                'county', county.geometry, place_id=props['GEOID'],
                name=props['NAME'], parent=state
            )
            counties.append(place)
        return counties

class Cities(object):
    """Census-designated places--basically cities and towns."""

    @classmethod
    def from_directory(cls, input_dir, states):
        for filename in sorted(os.listdir(input_dir)):
            if not filename.endswith("_place_500k.json"):
                continue
            for place in Cities.from_file(filename, states):
                yield place

    @classmethod
    def from_file(cls, filename, states):
        default_parent = None
        for place in features(filename):
            props = place.properties
            # Every place in a file should be from the same state, but
            # just in case, we check every time.
            parent = default_parent
            if 'ZCTA5CE10' in props:
                # This is a ZIP code. We're going to handle these
                # separately, later.
                continue
            if 'STATEFP' in props:
                state_id = props['STATEFP']
                parent = states.by_id[state_id]
                default_parent = parent
            name = props['NAME']
            parent.saw_place_name(name)
            yield Place('city', place.geometry, props['GEOID'], name, parent=parent)


class ZipCodes:

    @classmethod
    def process_geonames_file(cls, path, extra_info, nation, states):
        for i in open(path):
            country, zip_code, city, state, state_abbr = i.strip().split("\t")[:5]
            if country != 'US':
                # Geonames treats Puerto Rico et al. as different
                # countries; the Census Bureau treats them as states
                # in the United States.
                state_abbr = country
            if state_abbr in states.by_abbreviation:
                state = states.by_abbreviation[state_abbr]
            else:
                # A few ZIP codes in the Geonames data are associated
                # with the US armed forces, or with territories that
                # are not covered by the Census Bureau. For the sake
                # of completeness we will associate these ZIP codes
                # with the United States itself, but they shouldn't
                # come up, since we are only making Places out of ZIP
                # codes that have polygons in the Census Bureau data.
                #
                # 34034 (APO, Dillon, Armed Forces Americas)
                # 96373 (FPO, Adams, Armed Forces Pacific)
                # 96337 (APO, Harford, Armed Forces Pacific)
                # 96507 (DPO, Brazoria, Armed Forces Pacific)
                # 96208 (APO, Fulton, Armed Forces Pacific)
                # 96941 (Pohnpei, Federated States of Micronesia)
                # 96942 (Chuuk, Federated States of Micronesia)
                # 96943 (Yap, Federated States of Micronesia)
                # 96944 (Kosrae, Federated States of Micronesia)
                # 96960 (Majuro, Marshall Islands)
                # 96970 (Ebeye, Marshall Islands)
                # 96940 (Koror, Palau)
                state = nation
            extra_info[zip_code] = (city, state)

    @classmethod
    def from_filenames(cls, geonames_directory, cb_filename, nation, states):
        """
        Use Geonames information to associate a city name and a state with each ZIP code in the US (plus Puerto Rico).
        """
        extra_info = {} 
        for zipcode, (city, state_abbr) in EXTRA_ZIP_CODE_INFO.items():
            extra_info[zipcode] = (city, states.by_abbreviation[state_abbr])
        geonames_re = re.compile("[A-Z]{2}.txt")
        for geonames_file in os.listdir(geonames_directory):
            if not geonames_re.match(geonames_file):
                continue   # This is the readme

            geonames_file_path = GEONAMES_DIR / geonames_file
            cls.process_geonames_file(geonames_file_path, extra_info, nation, states)

        # Now process Census Bureau information to create an appropriate Place for each ZIP code.
        for data in features(cb_filename):
            props = data.properties
            zip_code = props['GEOID10']

            if zip_code in extra_info:
                city, state = extra_info[zip_code]
            else:
                city = None
                state = nation

            place = Place('postal_code', data.geometry, zip_code, name=zip_code, parent=state)

            # If there is no feature in this state with the name of this city, add it as an alias for a ZIP code.
            # This will help some (but not all) people who search for their neighborhood, a la "Forest Hills".
            if city and state != nation and city not in state.seen_names:
                place.aliases.add(city)

            yield place


def main():
    nation = Nation.from_filename(NATION_FILE)
    states = States.from_filename(STATES_FILE, nation)
    counties = Counties.from_filename(COUNTIES_FILE, states)
    cities = Cities.from_directory(GEOJSON_DIR, states)
    zipcodes = ZipCodes.from_filenames(GEONAMES_DIR, ZIPCODES_FILE, nation, states)

    print(nation.output)

    for state in states.by_id.values():
        print(state.output)

    for county in counties:
        print(county.output)

    for city in cities:
        print(city.output)

    for zipcode in zipcodes:
        print(zipcode.output)



if __name__ == '__main__':
    sys.exit(main())
