""" Configuration and utilities for RabbitMQ client.
    Mostly from eea.rabbitmq.plone
"""
import logging
import os
from contextlib import contextmanager

import transaction
from eea.rabbitmq.client.rabbitmq import RabbitMQConnector

logger = logging.getLogger("Reportek")
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter(
    "%(asctime)s - "
    "%(name)s/%(filename)s/%(funcName)s - "
    "%(levelname)s - %(message)s")
ch.setFormatter(formatter)
logger.addHandler(ch)

RABBITMQ_HOST = unicode(os.environ.get("RABBITMQ_HOST", "") or "localhost")
RABBITMQ_PORT = int(os.environ.get("RABBITMQ_PORT", "") or "5672")
RABBITMQ_USER = unicode(os.environ.get("RABBITMQ_USER", ""))
RABBITMQ_PASS = unicode(os.environ.get("RABBITMQ_PASS", ""))


def get_rabbitmq_client_settings():
    """ Return the settings from env variables
    """
    s = {}
    s['hostname'] = RABBITMQ_HOST
    s['port'] = RABBITMQ_PORT
    s['username'] = RABBITMQ_USER
    s['password'] = RABBITMQ_PASS
    return s


@contextmanager
def get_rabbitmq_conn(queue, context=None, dq=True):
    """ Context manager to connect to RabbitMQ
    """

    s = get_rabbitmq_client_settings()

    rb = RabbitMQConnector(s.get('hostname'),
                           s.get('port'),
                           s.get('username'),
                           s.get('password'))
    rb.open_connection()
    if dq:
        rb.declare_queue(queue)

    yield rb

    rb.close_connection()


@contextmanager
def get_rabbitmq_conn_nodqueue(queue, context=None):
    """ Context manager to connect to RabbitMQ
    """

    s = get_rabbitmq_client_settings()

    rb = RabbitMQConnector(s.get('hostname'),
                           s.get('port'),
                           s.get('username'),
                           s.get('password'))
    rb.open_connection()

    yield rb

    rb.close_connection()


def consume_messages(consumer, queue=None, context=None):
    """ Executes the callback on all messages existing in the queue
    """

    with get_rabbitmq_conn(queue, context) as conn:
        while not conn.is_queue_empty(queue):
            msg = conn.get_message(queue)
            consumer(msg)
            conn.get_channel().basic_ack(msg[0].delivery_tag)


class MessagesDataManager(object):
    """ Transaction aware data manager for RabbitMQ connections
    """

    def __init__(self):
        self.sp = 0
        self.messages = []
        self.txn = None

    @property
    def transaction(self):
        return self.txn

    @transaction.setter
    def transaction(self, value):
        self.txn = value

    def tpc_begin(self, txn):
        self.txn = txn

    def tpc_finish(self, txn):
        self.messages = []

    def tpc_vote(self, txn):
        # TODO: vote by trying to connect to rabbitmq server
        pass

    def tpc_abort(self, txn):
        self._checkTransaction(txn)

        if self.txn is not None:
            self.txn = None

        self.messages = []

    def abort(self, txn):
        self.messages = []

    def commit(self, txn):
        self._checkTransaction(txn)

        for queue, msg, dq in self.messages:
            count = 0
            for attempt in transaction.manager.attempts():
                try:
                    send_message(msg, queue=queue, dq=dq)
                    break
                except Exception as e:
                    count += 1
                    if count >= 3:
                        logger.exception(
                            "RabbitMQ Connection exception: {}".format(str(e)))
                        raise Exception(
                            '''Temporary network issue! Please
                             click the browser's back button and try again.''')

        self.txn = None
        self.messages = []

    def savepoint(self):
        self.sp += 1
        return Savepoint(self)

    def sortKey(self):
        return self.__class__.__name__

    def add(self, queue, msg, dq=True):
        logger.info("Add msg to queue: %s => %s", msg, queue)
        self.messages.append((queue, msg, dq))

    def _checkTransaction(self, txn):
        if (txn is not self.txn and self.txn is not None):
            raise TypeError("Transaction missmatch", txn, self.txn)


class Savepoint(object):
    """ Savepoint implementation to allow rollback of queued messages
    """

    def __init__(self, dm):
        self.dm = dm
        self.sp = dm.sp
        self.messages = dm.messages[:]
        self.transaction = dm.transaction

    def rollback(self):
        if self.transaction is not self.dm.transaction:
            raise TypeError("Attempt to rollback stale rollback")
        if self.dm.sp < self.sp:
            raise TypeError("Attempt to roll back to invalid save point",
                            self.sp, self.dm.sp)
        self.dm.sp = self.sp
        self.dm.messages = self.messages[:]


def send_message(msg, queue, context=None, dq=True):
    with get_rabbitmq_conn(queue=queue, context=context, dq=dq) as conn:
        conn.send_message(queue, msg)


def send_message_nodqueue(msg, queue, context=None):
    with get_rabbitmq_conn_nodqueue(queue=queue, context=context) as conn:
        conn.send_message(queue, msg)


def queue_msg(msg, queue=None, dq=True):
    """ Queues a rabbitmq message in the given queue
    """

    _mdm = MessagesDataManager()
    transaction.get().join(_mdm)
    _mdm.add(queue, msg, dq=dq)
