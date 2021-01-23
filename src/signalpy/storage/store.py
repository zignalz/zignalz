# SPDX-FileCopyrightText: 2020 Robert Cohn
#
# SPDX-License-Identifier: MIT

"""Persistent storage for objects.

"""

import logging
from abc import ABC, abstractmethod

import marshmallow as mm

import signalpy as sp

logger = logging.getLogger(__name__)


class Store(ABC):
    """Base class for persistent storage of objects.

    Parameters
    ----------
    db : :class:`~signalpy.storage.db.DB`
      Handle to DB
    name : str
      Name of store

    """

    def table(self, db, name):
        self.table = db.Table(db, name)

    @abstractmethod
    def create(db):
        """Create the persistent object in the db."""
        pass

    @abstractmethod
    def put(self, object):
        """Save an object.

        Parameters
        ----------
        object : object
          object with to_store method that returns a dict

        """
        pass

    @abstractmethod
    def query(self):
        """Returns list of objects matching filter."""
        pass


class SignalEventsStore(Store):
    """Stores events from devices."""

    table_name = 'SignalEvents'

    table_info = {
        'sqlite': {
            'schema': [
                ('signal_guid', 'text'),
                ('time', 'integer'),
                ('device_guid', 'text'),
                ('val', 'real'),
            ]
        },
        'dynamodb': {
            'KeySchema': [
                {'AttributeName': 'signal_guid', 'KeyType': 'HASH'},
                {'AttributeName': 'time', 'KeyType': 'RANGE'},
            ],
            'AttributeDefinitions': [
                {'AttributeName': 'signal_guid', 'AttributeType': 'S'},
                {'AttributeName': 'time', 'AttributeType': 'N'},
            ],
        },
    }

    class Schema(mm.Schema):
        """Schema for signal events."""

        time = mm.fields.Int()
        signal_guid = mm.fields.Str()
        device_guid = mm.fields.Str()
        val = mm.fields.Float()

    def __init__(self, db):
        self.table(db, SignalEventsStore.table_name)
        self.schema = SignalEventsStore.Schema()

    def create(db):
        db.create_table(
            SignalEventsStore.table_name, SignalEventsStore.table_info
        )
        return SignalEventsStore(db)

    def put(self, se):
        so = self.schema.dump(
            {
                'time': se.time,
                'signal_guid': se.signal.guid,
                'device_guid': se.device.guid,
                'val': se.val,
            }
        )
        self.table.put(so)

    def _make_signal_event(d):
        device = sp.Device.by_guid[d['device_guid']]
        signal = sp.Signal.by_guid[d['signal_guid']]
        return sp.SignalEvent(d['time'], device, signal, d['val'])

    def query(self):
        for o in self.table.query():
            do = dict(o)
            logger.info(f'SignalEventStore query result: {do}')
            so = self.schema.load(do)
            yield sp.SignalEventsStore._make_signal_event(so)


class AccountStore(Store):
    """Stores accounts."""

    table_name = 'Accounts'

    table_info = {
        'sqlite': {
            'schema': [
                ('guid', 'text'),
                ('name', 'text'),
                ('token', 'text'),
            ]
        },
        'dynamodb': {
            'KeySchema': [
                {'AttributeName': 'guid', 'KeyType': 'HASH'},
            ],
            'AttributeDefinitions': [
                {'AttributeName': 'guid', 'AttributeType': 'S'},
            ],
        },
    }

    class Schema(mm.Schema):
        """Schema for account store."""

        guid = mm.fields.Str()
        name = mm.fields.Str()
        token = mm.fields.Str()

        class Meta:
            unknown = mm.EXCLUDE

    def __init__(self, db):
        self.table(db, AccountStore.table_name)
        self.schema = AccountStore.Schema()

    def create(db):
        db.create_table(AccountStore.table_name, AccountStore.table_info)
        return AccountStore(db)

    def put(self, o):
        d = self.schema.dump(
            {
                'guid': o.guid,
                'name': o.name,
                'token': o.token,
            }
        )
        self.table.put(d)

    def _make_signal_event(d):
        device = sp.Device.by_guid[d['device_guid']]
        signal = sp.Signal.by_guid[d['signal_guid']]
        return sp.SignalEvent(d['time'], device, signal, d['val'])

    def query(self):
        for q in self.table.query():
            d = dict(q)
            logger.info(f'AccountStore query result: {d}')
            s_d = self.schema.load(d)
            yield sp.Account(
                guid=s_d['guid'], name=s_d['name'], token=s_d['token']
            )
