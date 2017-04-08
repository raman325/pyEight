"""
pyeight.user
~~~~~~~~~~~~~~~~~~~~
Provides user data for Eight Sleep
Copyright (c) 2017 John Mihalic <https://github.com/mezz64>
Licensed under the MIT license.

"""

import logging
from datetime import datetime, timedelta
import time
import asyncio

from pyeight.constants import (API_URL)

_LOGGER = logging.getLogger(__name__)

"""
Best way to structure this is to work to one HASS sensor for sleep data
and one for bed data for each side of the bed (if applicable).

Last Sleep Session sensor
_________________________________________
State will be the sleep score.
Attributes will be:
    Duration of awake, light, deep sleep
    Number of tosses and turns
    Average room temp
    Average bed temp
    Average respiritory rate
    Average heart rate
    Time spent heating

* These values are very dynamic during sleep so may only be useful
  when the "incomplete" parameter isn't present

Bed data sensor
_________________________________________
State will be current heating level
Attributes will be:
    Target heating level
    Heating Active (true/false)
    Heating duration remaining
    Time last seen in-bed

"""


class EightUser(object):
    """Class for handling data of each eight user."""
    def __init__(self, device, userid, side):
        """Initialize user class."""
        self.device = device
        self.userid = userid
        self.side = side

        self.trends = None
        self.intervals = None
        self.data = device.device_data

        # Variables to do dynamic presence
        self.past_heating_level = None
        self.presence = False

    @property
    def bed_presence(self):
        """Return true/false for bed presence."""
        return self.presence

    @property
    def target_heating_level(self):
        """Return target heating level."""
        try:
            if self.side == 'Left':
                level = self.device.device_data['leftTargetHeatingLevel']
            elif self.side == 'Right':
                level = self.device.device_data['rightTargetHeatingLevel']
            return level
        except TypeError:
            return None

    @property
    def heating_level(self):
        """Return heating level."""
        try:
            if self.side == 'Left':
                level = self.device.device_data['leftHeatingLevel']
            elif self.side == 'Right':
                level = self.device.device_data['rightHeatingLevel']
            return level
        except TypeError:
            return None

    @property
    def now_heating(self):
        """Return current heating state."""
        try:
            if self.side == 'Left':
                heat = self.device.device_data['leftNowHeating']
            elif self.side == 'Right':
                heat = self.device.device_data['rightNowHeating']
            return heat
        except TypeError:
            return None

    @property
    def heating_remaining(self):
        """Return seconds of heat time remaining."""
        try:
            if self.side == 'Left':
                timerem = self.device.device_data['leftHeatingDuration']
            elif self.side == 'Right':
                timerem = self.device.device_data['rightHeatingDuration']
            return timerem
        except TypeError:
            return None

    @property
    def heating_values(self):
        """Return a dict of all the current heating values."""
        heating_dict = {
            'level': self.heating_level,
            'target': self.target_heating_level,
            'active': self.now_heating,
            'remaining': self.heating_remaining,
        }
        return heating_dict

    @property
    def current_session_date(self):
        """Return date/time for start of last session data."""
        try:
            incomplete = self.intervals[0]['incomplete']
            if incomplete is True:
                date = self.intervals[0]['ts']
                date_f = datetime.strptime(date, '%Y-%m-%dT%H:%M:%S.%fZ')
                now = time.time()
                offset = datetime.fromtimestamp(now) \
                    - datetime.utcfromtimestamp(now)
                date = date_f + offset
        except KeyError:
            # No active sessions, top result is last complete session.
            date = None
        return date

    @property
    def current_sleep_stage(self):
        """Return sleep stage for in-progress session."""
        try:
            incomplete = self.intervals[0]['incomplete']
            if incomplete is True:
                stages = self.intervals[0]['stages']
                num_stages = len(stages)
                stage = stages[num_stages-1]['stage']
        except KeyError:
            # No active sessions, top result is last complete session.
            stage = None
        return stage

    @property
    def current_sleep_score(self):
        """Return sleep score for in-progress session."""
        # Check most recent result to see if it's incomplete.
        try:
            incomplete = self.intervals[0]['incomplete']
            if incomplete is True:
                score = self.intervals[0]['score']
        except KeyError:
            # No active sessions, top result is last complete session.
            score = None
        return score

    @property
    def current_sleep_breakdown(self):
        """Return durations of sleep stages for in-progress session."""
        try:
            incomplete = self.intervals[0]['incomplete']
            if incomplete is True:
                stages = self.intervals[0]['stages']
                breakdown = {'awake': 0, 'light': 0, 'deep': 0}
                for stage in stages:
                    if stage['stage'] == 'awake':
                        breakdown['awake'] += stage['duration']
                    elif stage['stage'] == 'light':
                        breakdown['light'] += stage['duration']
                    elif stage['stage'] == 'deep':
                        breakdown['deep'] += stage['duration']
        except KeyError:
            # No active sessions, top result is last complete session.
            breakdown = None
        return breakdown

    @property
    def current_bed_temp(self):
        """Return current bed temperature for in-progress session."""
        try:
            incomplete = self.intervals[0]['incomplete']
            if incomplete is True:
                bedtemps = self.intervals[0]['timeseries']['tempBedC']
                num_temps = len(bedtemps)
                bedtemp = bedtemps[num_temps-1][1]
        except KeyError:
            # No active sessions, top result is last complete session.
            bedtemp = None
        return bedtemp

    @property
    def current_room_temp(self):
        """Return current room temperature for in-progress session."""
        try:
            incomplete = self.intervals[0]['incomplete']
            if incomplete is True:
                rmtemps = self.intervals[0]['timeseries']['tempRoomC']
                num_temps = len(rmtemps)
                rmtemp = rmtemps[num_temps-1][1]
        except KeyError:
            # No active sessions, top result is last complete session.
            rmtemp = None
        return rmtemp

    @property
    def current_tnt(self):
        """Return current toss & turns for in-progress session."""
        try:
            incomplete = self.intervals[0]['incomplete']
            if incomplete is True:
                tnt = len(self.intervals[0]['timeseries']['tnt'])
        except KeyError:
            # No active sessions, top result is last complete session.
            tnt = None
        return tnt

    @property
    def current_resp_rate(self):
        """Return current respiratory rate for in-progress session."""
        try:
            incomplete = self.intervals[0]['incomplete']
            if incomplete is True:
                rates = self.intervals[0]['timeseries']['respiratoryRate']
                num_rates = len(rates)
                rate = rates[num_rates-1][1]
        except KeyError:
            # No active sessions, top result is last complete session.
            rate = None
        return rate

    @property
    def current_heart_rate(self):
        """Return current heart rate for in-progress session."""
        try:
            incomplete = self.intervals[0]['incomplete']
            if incomplete is True:
                rates = self.intervals[0]['timeseries']['heartRate']
                num_rates = len(rates)
                rate = rates[num_rates-1][1]
        except KeyError:
            # No active sessions, top result is last complete session.
            rate = None
        return rate

    @property
    def current_values(self):
        """Return a dict of all the 'current' parameters."""
        current_dict = {
            'date': self.current_session_date,
            'score': self.current_sleep_score,
            'stage': self.current_sleep_stage,
            'breakdown': self.current_sleep_breakdown,
            'tnt': self.current_tnt,
            'bed_temp': self.current_bed_temp,
            'room_temp': self.current_room_temp,
            'resp_rate': self.current_resp_rate,
            'heart_rate': self.current_heart_rate,
        }
        return current_dict

    @property
    def last_session_date(self):
        """Return date/time for start of last session data."""
        try:
            incomplete = self.intervals[0]['incomplete']
            if incomplete is True:
                date = self.intervals[1]['ts']
        except KeyError:
            # No active sessions, top result is last complete session.
            date = self.intervals[0]['ts']
        date_f = datetime.strptime(date, '%Y-%m-%dT%H:%M:%S.%fZ')
        now = time.time()
        offset = datetime.fromtimestamp(now) - datetime.utcfromtimestamp(now)
        return date_f + offset

    @property
    def last_sleep_score(self):
        """Return sleep score from last complete sleep session."""
        # Check most recent result to see if it's incomplete.
        try:
            incomplete = self.intervals[0]['incomplete']
            if incomplete is True:
                score = self.intervals[1]['score']
        except KeyError:
            # No active sessions, top result is last complete session.
            score = self.intervals[0]['score']
        return score

    @property
    def last_sleep_breakdown(self):
        """Return durations of sleep stages for last complete session."""
        try:
            incomplete = self.intervals[0]['incomplete']
            if incomplete is True:
                stages = self.intervals[1]['stages']
        except KeyError:
            # No active sessions, top result is last complete session.
            stages = self.intervals[0]['stages']

        breakdown = {'awake': 0, 'light': 0, 'deep': 0}
        for stage in stages:
            if stage['stage'] == 'awake':
                breakdown['awake'] += stage['duration']
            elif stage['stage'] == 'light':
                breakdown['light'] += stage['duration']
            elif stage['stage'] == 'deep':
                breakdown['deep'] += stage['duration']
        return breakdown

    @property
    def last_bed_temp(self):
        """Return avg bed temperature for last session."""
        try:
            incomplete = self.intervals[0]['incomplete']
            if incomplete is True:
                bedtemps = self.intervals[1]['timeseries']['tempBedC']
        except KeyError:
            # No active sessions, top result is last complete session.
            bedtemps = self.intervals[0]['timeseries']['tempBedC']
        tmp = 0
        num_temps = len(bedtemps)
        for temp in bedtemps:
            tmp += temp[1]
        bedtemp = tmp/num_temps
        return bedtemp

    @property
    def last_room_temp(self):
        """Return avg room temperature for last session."""
        try:
            incomplete = self.intervals[0]['incomplete']
            if incomplete is True:
                rmtemps = self.intervals[1]['timeseries']['tempRoomC']
        except KeyError:
            # No active sessions, top result is last complete session.
            rmtemps = self.intervals[0]['timeseries']['tempRoomC']
        tmp = 0
        num_temps = len(rmtemps)
        for temp in rmtemps:
            tmp += temp[1]
        rmtemp = tmp/num_temps
        return rmtemp

    @property
    def last_tnt(self):
        """Return toss & turns for last session."""
        try:
            incomplete = self.intervals[0]['incomplete']
            if incomplete is True:
                tnt = len(self.intervals[1]['timeseries']['tnt'])
        except KeyError:
            # No active sessions, top result is last complete session.
            tnt = len(self.intervals[0]['timeseries']['tnt'])
        return tnt

    @property
    def last_resp_rate(self):
        """Return avg respiratory rate for last session."""
        try:
            incomplete = self.intervals[0]['incomplete']
            if incomplete is True:
                rates = self.intervals[1]['timeseries']['respiratoryRate']
        except KeyError:
            # No active sessions, top result is last complete session.
            rates = self.intervals[0]['timeseries']['respiratoryRate']
        tmp = 0
        num_rates = len(rates)
        for rate in rates:
            tmp += rate[1]
        rateavg = tmp/num_rates
        return rateavg

    @property
    def last_heart_rate(self):
        """Return avg heart rate for last session."""
        try:
            incomplete = self.intervals[0]['incomplete']
            if incomplete is True:
                rates = self.intervals[1]['timeseries']['heartRate']
        except KeyError:
            # No active sessions, top result is last complete session.
            rates = self.intervals[0]['timeseries']['heartRate']
        tmp = 0
        num_rates = len(rates)
        for rate in rates:
            tmp += rate[1]
        rateavg = tmp/num_rates
        return rateavg

    @property
    def last_values(self):
        """Return a dict of all the 'last' parameters."""
        last_dict = {
            'date': self.last_session_date,
            'score': self.last_sleep_score,
            'breakdown': self.last_sleep_breakdown,
            'tnt': self.last_tnt,
            'bed_temp': self.last_bed_temp,
            'room_temp': self.last_room_temp,
            'resp_rate': self.last_resp_rate,
            'heart_rate': self.last_heart_rate,
        }
        return last_dict

    def dynamic_presence(self):
        """
        Determine presence based on bed heating level.

        Method originated from Alex Lee Yuk Cheung SmartThings Code.
        """
        if self.now_heating:
            heat_delta = self.heating_level - self.target_heating_level
        elif self.heating_level is not None:
            heat_delta = self.heating_level - 10
        else:
            heat_delta = 0

        if heat_delta >= 8 and self.heating_level >= 25:
            # Someone is likely in bed
            self.presence = True

        if not self.now_heating and self.heating_level <= 15:
            # Someone is not likely in bed
            self.presence = False
        elif self.now_heating and heat_delta < 8:
            # Also a no bed condition
            self.presence = False

        # Need to do logging tests to check rate of change over a 1 minute
        # sampling interval for someone getting into and out of bed.

    @asyncio.coroutine
    def update_user(self):
        """Update all user data."""
        self.past_heating_level = self.heating_level
        yield from self.update_intervals_data()
        # now = datetime.today()
        # start = now - timedelta(days=2)
        # end = now + timedelta(days=2)
        # yield from self.update_trend_data(start.strftime('%Y-%m-%d'),
        #                                  end.strftime('%Y-%m-%d'))
        # self.dynamic_presence()

    @asyncio.coroutine
    def set_heating_level(self, level, duration):
        """Update heating data json."""
        url = '{}/devices/{}'.format(API_URL, self.device.deviceid)

        # Catch bad inputs
        level = 10 if level < 10 else level
        level = 100 if level > 100 else level

        if self.side == 'Left':
            data = {
                'leftHeatingDuration': duration,
                'leftTargetHeatingLevel': level
            }
        elif self.side == 'Right':
            data = {
                'rightHeatingDuration': duration,
                'rightTargetHeatingLevel': level
            }

        set_heat = yield from self.device.api_put(url, data)
        if set_heat is None:
            _LOGGER.error('Unable to set eight heating level.')
        else:
            _LOGGER.debug('Heating Result: %s', set_heat)

    @asyncio.coroutine
    def update_trend_data(self, startdate, enddate):
        """Update trends data json for specified time period."""
        url = '{}/users/{}/trends'.format(API_URL, self.userid)
        params = {
            'tz': self.device.tzone,
            'from': startdate,
            'to': enddate
            }

        trends = yield from self.device.api_get(url, params)
        if trends is None:
            _LOGGER.error('Unable to fetch eight trend data.')
        else:
            # _LOGGER.debug('Trend Result: %s', trends)
            self.trends = trends['days']

    @asyncio.coroutine
    def update_intervals_data(self):
        """Update intervals data json for specified time period."""
        url = '{}/users/{}/intervals'.format(API_URL, self.userid)

        intervals = yield from self.device.api_get(url)
        if intervals is None:
            _LOGGER.error('Unable to fetch eight intervals data.')
        else:
            # _LOGGER.debug('Intervals Result: %s', intervals)
            self.intervals = intervals['intervals']
