##############################################################################
#
# Copyright (c) 2001 Zope Corporation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.0 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE
#
##############################################################################
"""Handy standard storage machinery

$Id: base.py,v 1.33 2003/09/12 14:45:33 chrisw Exp $
"""

__metaclass__ = type

import os
import time
import errno
import shutil
import struct
import sys
import threading
import logging

# In Python 2.3, we can simply use the bsddb module, but for Python 2.2, we
# need to use pybsddb3, a.k.a. bsddb3.
try:
    try:
        from bsddb import db
    except ImportError:
        from bsddb3 import db
    berkeley_is_available = True
except ImportError:
    berkeley_is_available = False
    # If we're supposed to be running all tests, output a warning
    if os.environ.get("COMPLAIN_IF_TESTS_MISSED"):
        sys.stderr.write("bsdbb not available, some tests disabled\n")        

    # But, MemoryStorage piggybacks on the implementation of BDBFullStorage so
    # create a fake db object that has some useful constants.
    class db:
        DB_QUEUE = 1
        DB_DUP = 2
        DB_FORCE = 3

        class DBNotFoundError(Exception): pass
        class DBKeyEmpty(Exception): pass

from zodb.conflict import ConflictResolver
from zodb.timestamp import newTimeStamp, TimeStamp
from zodb.interfaces import ITransactionAttrs, ZERO
from zodb.storage.interfaces import StorageTransactionError, ReadOnlyError
# BaseStorage provides primitives for lock acquisition and release, and a host
# of other methods, some of which are overridden here, some of which are not.
from zodb.lockfile import LockFile
from zodb.utils import p64, u64

GBYTES = 1024 * 1024 * 1000
JOIN_TIME = 10

class PackStop(Exception):
    """Escape hatch for pack operations."""



class BaseStorage:
    """Abstract base class that support storage implementations.

    A subclass must define the following methods:
    load()
    close()
    cleanup()
    lastSerial()
    lastTransaction()
    XXX the previous two should be provided by base

    _begin()
    _vote()
    _abort()
    _finish()
    _clear_temp()

    If the subclass wants to implement IUndoStorage, it must implement
    all the methods in that interface.

    If the subclass wants to implement IVersionStorage, it must implement
    all the methods in that interface.

    Each storage will have two locks that are accessed via lock
    acquire and release methods bound to the instance.  (Yuck.)
    _lock_acquire / _lock_release (reentrant)
    _commit_lock_acquire / _commit_lock_release

    The commit lock is acquired in tpcBegin() and released in
    tpcAbort() and tpcFinish().  It is never acquired with the other
    lock held.

    The other lock appears to protect _oid and _transaction and
    perhaps other things.  It is always held when load() is called, so
    presumably the load() implementation should also acquire the lock.
    """

    _transaction = None # Transaction that is being committed
    _serial = ZERO      # Transaction serial number
    _tstatus = ' '      # Transaction status, used for copying data
    _is_read_only = False
    _version = None

    def __init__(self, name):
        self._name = name

        # Allocate locks:
        l = threading.RLock()
        self._lock_acquire = l.acquire
        self._lock_release = l.release
        # XXX Should use a condition variable here
        l = threading.Lock()
        self._commit_lock_acquire = l.acquire
        self._commit_lock_release = l.release

        self._ts = newTimeStamp()
        self._serial = self._ts.raw()
        self._oid = ZERO
        self._ltid = ZERO

    def lastTransaction(self):
        """Return transaction id for last committed transaction.

        If no transactions have yet been committed, return ZERO.
        """
        return self._ltid

    def abortVersion(self, src, transaction):
        if transaction is not self._transaction:
            raise StorageTransactionError(self, transaction)
        return []

    def commitVersion(self, src, dest, transaction):
        if transaction is not self._transaction:
            raise StorageTransactionError(self, transaction)
        return []

    def sortKey(self):
        # An implementation should override this if it can be shared
        # by multiple processes and / or guarantee that self._name is
        # uniquely defines the storage across all procsses.
        return self._name

    def getName(self):
        return self._name

    def getVersion(self):
        return self._version

    def setVersion(self, version):
        self._version = version

    def modifiedInVersion(self, oid):
        return ''

    def newObjectId(self):
        if self._is_read_only:
            raise ReadOnlyError
        self._lock_acquire()
        try:
            self._oid = p64(u64(self._oid) + 1)
            return self._oid
        finally:
            self._lock_release()

    def lastObjectId(self):
        return self._oid

    def registerDB(self, db):
        pass # we don't care

    def isReadOnly(self):
        return self._is_read_only

    def _clear_temp(self):
        # Called by tpc_begin(), tpc_abort(), and tpc_finish(), this should be
        # overridden in storages to clear out any temporary state.
        pass

    def tpcAbort(self, transaction):
        self._lock_acquire()
        try:
            if transaction is not self._transaction:
                return
            self._abort()
            self._clear_temp()
            self._transaction = None
            self._commit_lock_release()
        finally:
            self._lock_release()

    def _abort(self):
        # Subclasses should define this to supply abort actions.
        pass

    def tpcBegin(self, transaction, tid=None, status=' '):
        assert ITransactionAttrs.isImplementedBy(transaction)
        if self._is_read_only:
            raise ReadOnlyError()
        self._lock_acquire()
        try:
            if self._transaction is transaction:
                return
            self._lock_release()
            self._commit_lock_acquire()
            self._lock_acquire()
            self._transaction = transaction
            self._clear_temp()

            # The user and description fields may be Unicode with non-ASCII
            # characters in them.  Convert them to utf-8 for the convenience
            # of derived storages.
            user = transaction.user.encode('utf-8')
            desc = transaction.description.encode('utf-8')
            # The transaction extension should be a mapping, which we'll
            # pickle also for the convenience of derived storages.
            if transaction._extension:
                import cPickle
                ext = cPickle.dumps(transaction._extension, 1)
            else:
                ext = ""
            self._ude = user, desc, ext
            if tid is None:
                self._ts = newTimeStamp(self._ts)
                self._serial = self._ts.raw()
            else:
                self._ts = TimeStamp(tid)
                self._serial = tid
            self._tstatus = status
            self._begin(self._serial)
        finally:
            self._lock_release()

    def _begin(self, tid):
        # Subclasses should define this to supply transaction start actions.
        pass

    def tpcVote(self, transaction):
        self._lock_acquire()
        try:
            if transaction is not self._transaction:
                return
            self._vote()
        finally:
            self._lock_release()

    def _vote(self):
        # Subclasses should define this to supply transaction vote actions.
        pass

    def tpcFinish(self, transaction, f=None):
        self._lock_acquire()
        try:
            if transaction is not self._transaction:
                return
            try:
                if f is not None:
                    f()
                self._finish(self._serial)
                self._clear_temp()
            finally:
                self._ude = None
                self._transaction = None
                self._commit_lock_release()
        finally:
            self._lock_release()

    def _finish(self, tid):
        # Subclasses should define this to supply transaction finish actions.
        pass

    # XXX should remove undoLog() and only export undoInfo()

    def undoInfo(self, first=0, last=-20, specification=None):
        """Return a list of transaction descriptions for use with undo.

        The first and last argument specify how many transactions to
        return and where in the transaction history they should come
        from.  The specification argument is a mapping that specifies
        a filter on transaction metadata.

        undoInfo() scans the transaction history from most recent
        transaction to oldest transaction.  It skips the 'first' most
        recent transactions; i.e. if first is N, then the first
        transaction returned will be the Nth transaction.

        If last is less than zero, then its absolute value is the
        maximum number of transactions to return.  Otherwise if last
        is N, then only the N most recent transactions following start
        are considered.

        If specification is not None, then it must be a mapping that
        is compared to the transaction description.  Each key-value
        pair in the specification must also be present in the
        description.
        """
        if specification:
            def filter(desc, spec=specification.items()):
                for k, v in spec:
                    if desc.get(k) != v:
                        return False
                return True
        else:
            filter = None
        return self.undoLog(first, last, filter)

    def undoLog(self, first=0, last=-20, filter=None):
        return ()

    def versionEmpty(self, version):
        return True

    def versions(self, max=None):
        return ()

    def pack(self, t, gc=True):
        if self._is_read_only:
            raise ReadOnlyError()

    def getSerial(self, oid):
        self._lock_acquire()
        try:
            v = self.modifiedInVersion(oid)
            pickledata, serial = self.load(oid, v)
            return serial
        finally:
            self._lock_release()

    def loadSerial(self, oid, serial):
        raise NotImplementedError

    def getExtensionMethods(self):
        """getExtensionMethods

        This returns a dictionary whose keys are names of extra methods
        provided by this storage. Storage proxies (such as ZEO) should
        call this method to determine the extra methods that they need
        to proxy in addition to the standard storage methods.
        Dictionary values should be None; this will be a handy place
        for extra marshalling information, should we need it
        """
        return {}

    def copyTransactionsFrom(self, other, verbose=0):
        """Copy transactions from another storage.

        This is typically used for converting data from one storage to
        another.
        """
        _ts = None
        ok = True
        for transaction in other.iterator():
            tid = transaction.tid
            if _ts is None:
                _ts = TimeStamp(tid)
            else:
                t = TimeStamp(tid)
                if t <= _ts:
                    if ok:
                        print ('Time stamps out of order %s, %s' % (_ts, t))
                    ok = False
                    _ts = t.laterThan(_ts)
                    tid = _ts.raw()
                else:
                    _ts = t
                    if not ok:
                        print ('Time stamps back in order %s' % (t))
                        ok = True

            if verbose:
                print _ts

            self.tpcBegin(transaction, tid, transaction.status)
            for r in transaction:
                if verbose:
                    print `r.oid`, r.version, len(r.data)
                self.restore(r.oid, r.serial, r.data, r.refs, r.version,
                             r.data_txn, transaction)
            self.tpcVote(transaction)
            self.tpcFinish(transaction)

# A couple of convenience methods
def splitrefs(refstr, oidlen=8):
    # refstr is a packed string of reference oids.  Always return a list of
    # oid strings.  Most storages use fixed oid lengths of 8 bytes, but if
    # the oids in refstr are a different size, use oidlen to specify.  This
    # does /not/ support variable length oids in refstr.
    if not refstr:
        return []
    num, extra = divmod(len(refstr), oidlen)
    fmt = '%ds' % oidlen
    assert extra == 0, refstr
    return list(struct.unpack('>' + (fmt * num), refstr))



class BerkeleyConfig:
    """Bag of attributes for configuring Berkeley based storages.

    Berkeley databases are wildly configurable, and this class exposes some of
    that.  To customize these options, instantiate one of these classes and
    set the attributes below to the desired value.  Then pass this instance to
    the Berkeley storage constructor, using the `config' keyword argument.

    BerkeleyDB stores all its information in an `environment directory'
    (modulo log files, which can be in a different directory, see below).  By
    default, the `name' argument given to the storage constructor names this
    directory, but you can set this option to explicitly point to a different
    location:

    - envdir if not None, names the BerkeleyDB environment directory.  The
      directory will be created if necessary, but its parent directory must
      exist.  Additional configuration is available through the BerkeleyDB
      DB_CONFIG mechanism.

    Berkeley storages need to be checkpointed occasionally, otherwise
    automatic recovery can take a huge amount of time.  You should set up a
    checkpointing policy which trades off the amount of work done periodically
    against the recovery time.  Note that the Berkeley environment is
    automatically, and forcefully, checkpointed twice when it is closed.

    The following checkpointing attributes are supported:

    - interval indicates how often, in seconds, a Berkeley checkpoint is
      performed.  If this is non-zero, checkpointing is performed by a
      background thread.  Otherwise checkpointing will only be done when the
      storage is closed.   You really want to enable checkpointing. ;)

    - kbytes is passed directly to txn_checkpoint()

    - min is passed directly to txn_checkpoint()

    You can achieve one of the biggest performance wins by moving the Berkeley
    log files to a different disk than the data files.  We saw between 2.5 and
    7 x better performance this way.  Here are attributes which control the
    log files.

    - logdir if not None, is passed to the environment's set_lg_dir() method
      before it is opened.

    You can also improve performance by tweaking the Berkeley cache size.
    Berkeley's default cache size is 256KB which is usually too small.  Our
    default cache size is 128MB which seems like a useful tradeoff between
    resource consumption and improved performance.  You might be able to get
    slightly better results by turning up the cache size, although be mindful
    of your system's limits.  See here for more details:

        http://www.sleepycat.com/docs/ref/am_conf/cachesize.html

    These attributes control cache size settings:

    - cachesize should be the size of the cache in bytes.

    These attributes control the autopacking thread:

    - frequency is the time in seconds after which an autopack phase will be
      performed.  E.g. if frequency is 3600, an autopack will be done once per
      hour.  Set frequency to 0 to disable autopacking (the default).

    - packtime is the time in seconds marking the moment in the past at which
      to autopack to.  E.g. if packtime is 14400, autopack will pack to 4
      hours in the past.  For Minimal storage, this value is ignored.

    - gcpack is an integer indicating how often an autopack phase should do a
      full garbage collecting pack.  E.g. if gcpack is 24 and frequence is
      3600, a gc pack will be performed once per day.  Set to zero to never
      automatically do gc packs.  For Minimal storage, this value is ignored;
      all packs are gc packs.

    Here are some other miscellaneous configuration variables:

    - read_only causes ReadOnlyError's to be raised whenever any operation
      (except pack!) might modify the underlying database.
    """
    envdir = None
    interval = 120
    kbyte = 0
    min = 0
    logdir = None
    cachesize = 128 * 1024 * 1024
    frequency = 0
    packtime = 4 * 60 * 60
    gcpack = 0
    read_only = False

    def __repr__(self):
        d = self.__class__.__dict__.copy()
        d.update(self.__dict__)
        return """<BerkeleyConfig (read_only=%(read_only)s):
\tenvironment dir:: %(envdir)s
\tcheckpoint interval: %(interval)s seconds
\tcheckpoint kbytes: %(kbyte)s
\tcheckpoint minutes: %(min)s
\t----------------------
\tlogdir: %(logdir)s
\tcachesize: %(cachesize)s bytes
\t----------------------
\tautopack frequency: %(frequency)s seconds
\tpack to %(packtime)s seconds in the past
\tclassic pack every %(gcpack)s autopacks
\t>""" % d



class BerkeleyBase(BaseStorage):
    """Base storage for Minimal and Full Berkeley implementations."""

    def __init__(self, name, config=None):
        """Create a new storage.

        name is an arbitrary name for this storage.  It is returned by the
        getName() method.  If the config object's envdir attribute is None,
        then name also points to the BerkeleyDB environment directory.

        Optional config must be a BerkeleyConfig instance, or None, which
        means to use the default configuration options.
        """
        # sanity check arguments
        if config is None:
            config = BerkeleyConfig()
        self._config = config

        if name == '':
            raise TypeError, 'database name is empty'

        logger = logging.getLogger(self.__class__.__name__)
        self.log = logger.info

        self.log('Creating Berkeley environment')
        envdir = config.envdir or name
        self.log('Berkeley environment dir: %s', envdir)
        self._env, self._lockfile = self._newenv(envdir)

        BaseStorage.__init__(self, envdir)
        self._is_read_only = config.read_only
        self._conflict = ConflictResolver(self)

        # Instantiate a pack lock
        self._packlock = threading.Lock()
        self._stop = False
        self._closed = False
        self._packing = False
        # Create some tables that are common between the storages, then give
        # the storages a chance to create a few more tables.
        self._tables = []
        self._info = self._setupDB('info')
        self._serials = self._setupDB('serials', db.DB_DUP)
        self._pickles = self._setupDB('pickles')
        self._refcounts = self._setupDB('refcounts')
        self._references = self._setupDB('references')
        self._oids = self._setupDB('oids')
        self._pending = self._setupDB('pending')
        self._packmark = self._setupDB('packmark', db.DB_DUP)
        # Do storage specific initialization
        self._init()
        self._withtxn(self._version_check)
        self._withlock(self._dorecovery)
        # Initialize the object id counter.
        self._init_oid()
        # Set up the checkpointing thread
        self.log('setting up threads')
        if config.interval > 0:
            self._checkpointstop = event = threading.Event()
            self._checkpointer = _Checkpoint(self, event, config.interval)
            self._checkpointer.start()
        else:
            self._checkpointer = None
        # Set up the autopacking thread
        if config.frequency > 0:
            self._autopackstop = event = threading.Event()
            self._autopacker = self._make_autopacker(event)
            self._autopacker.start()
        else:
            self._autopacker = None
        self.log('ready')

    def _init(self):
        raise NotImplementedError

    def _newenv(self, envdir):
        # Use the absolute path to the environment directory as the name.
        # This should be enough of a guarantee that sortKey() -- which via
        # BaseStorage uses the name -- is globally unique.
        envdir = os.path.abspath(envdir)
        return env_from_string(envdir, self._config)

    def _version_check(self):
        raise NotImplementedError

    def _dorecovery(self):
        raise NotImplementedError

    def _make_autopacker(self, event):
        raise NotImplementedError

    def _setupDB(self, name, flags=0, dbtype=None, reclen=None):
        """Open an individual database with the given flags.

        flags are passed directly to the underlying DB.set_flags() call.
        Optional dbtype specifies the type of BerkeleyDB access method to
        use.  Optional reclen if not None gives the record length.
        """
        if dbtype is None:
            dbtype = db.DB_BTREE
        d = db.DB(self._env)
        if flags:
            d.set_flags(flags)
        # Our storage is based on the underlying BSDDB btree database type.
        if reclen is not None:
            d.set_re_len(reclen)
        # DB 4.1 requires that operations happening in a transaction must be
        # performed on a database that was opened in a transaction.  Since we
        # do the former, we must do the latter.  However, earlier DB versions
        # don't transactionally protect database open, so this is the most
        # portable way to write the code.
        openflags = db.DB_CREATE
        try:
            openflags |= db.DB_AUTO_COMMIT
        except AttributeError:
            pass
        d.open('zodb_' + name, dbtype, openflags)
        self._tables.append(d)
        return d

    def _init_oid(self):
        """Initialize the object id counter."""
        # If the `serials' database is non-empty, the last object id in the
        # database will be returned (as a [key, value] pair).  Use it to
        # initialize the object id counter.
        #
        # If the database is empty, just initialize it to zero.
        value = self._serials.cursor().last()
        if value:
            self._oid = value[0]
        else:
            self._oid = ZERO

    # It can be very expensive to calculate the "length" of the database, so
    # we cache the length and adjust it as we add and remove objects.
    _len = None

    def __len__(self):
        """Return the number of objects in the index."""
        if self._len is None:
            # The cache has never been initialized.  Do it once the expensive
            # way.
            self._len = len(self._serials)
        return self._len

    def newObjectId(self):
        """Create a new object id."""
        newoid = BaseStorage.newObjectId(self)
        if self._len is not None:
            # Increment the cached length
            self._len += 1
        return newoid

    def getSize(self):
        """Return the size of the database."""
        # Return the size of the pickles table as a rough estimate
        filename = os.path.join(self._env.db_home, 'zodb_pickles')
        return os.path.getsize(filename)

    def _vote(self):
        pass

    def _finish(self, tid):
        self._withtxn(self._docommit, self._serial)
        self._ltid = tid

    def _abort(self):
        raise NotImplementedError

    def _clear_temp(self):
        # This method is called from BaseStorage's tpcBegin(), tpcAbort() and
        # tpcFinish(), but the Berkeley storages don't have a temp file.
        pass

    def _setVersion(self, txn, vstr):
        self._info.put('dbversion', vstr, txn=txn)

    def setVersion(self, version):
        self._withtxn(self._setVersion, version)

    def getVersion(self):
        return self._info.get('dbversion')

    def close(self):
        """Close the storage.

        All background threads are stopped and joined first, then all the
        tables are closed, and finally the environment is force checkpointed
        and closed too.
        """
        # We have to shutdown the background threads before we acquire the
        # lock, or we'll could end up closing the environment before the
        # autopacking thread exits.
        self._stop = True
        # Stop the autopacker thread
        if self._autopacker:
            self.log('stopping autopacking thread')
            # Setting the event also toggles the stop flag
            self._autopackstop.set()
            self._autopacker.join(JOIN_TIME)
        if self._checkpointer:
            self.log('stopping checkpointing thread')
            # Setting the event also toggles the stop flag
            self._checkpointstop.set()
            self._checkpointer.join(JOIN_TIME)
        self._lock_acquire()
        try:
            if not self._closed:
                self._doclose()
                self._closed = True
        finally:
            self._lock_release()
        self.log('finished closing the database')

    def _doclose(self):
        # Close all the tables
        for d in self._tables:
            d.close()
        # As recommended by Keith Bostic @ Sleepycat, we need to do
        # two checkpoints just before we close the environment.
        # Otherwise, auto-recovery on environment opens can be
        # extremely costly.  We want to do auto-recovery for ease of
        # use, although they aren't strictly necessary if the database
        # was shutdown gracefully.  The DB_FORCE flag is required for
        # the second checkpoint, but we include it in both because it
        # can't hurt and is more robust.
        self._env.txn_checkpoint(0, 0, db.DB_FORCE)
        self._env.txn_checkpoint(0, 0, db.DB_FORCE)
        self._lockfile.close()
        self._env.close()

    # A couple of convenience methods
    def _update(self, deltas, references, incdec):
        for oid in splitrefs(references):
            rc = deltas.get(oid, 0) + incdec
            if rc == 0:
                # Save space in the dict by zapping zeroes
                del deltas[oid]
            else:
                deltas[oid] = rc

    def _withlock(self, meth, *args):
        self._lock_acquire()
        try:
            return meth(*args)
        finally:
            self._lock_release()

    def _withtxn(self, meth, *args, **kws):
        txn = self._env.txn_begin()
        try:
            ret = meth(txn, *args, **kws)
        except PackStop:
            # Escape hatch for shutdown during pack.  Like the bare except --
            # i.e. abort the transaction -- but swallow the exception.
            txn.abort()
        except:
            #import traceback ; traceback.print_exc()
            txn.abort()
            raise
        else:
            txn.commit()
            return ret

    def docheckpoint(self):
        config = self._config
        self._lock_acquire()
        try:
            if not self._stop:
                self._env.txn_checkpoint(config.kbyte, config.min)
        finally:
            self._lock_release()

    def cleanup(self):
        """Remove the entire environment directory for this storage."""
        cleanup(self.getName())



def env_from_string(envdir, config):
    # BSDDB requires that the directory already exists.  BAW: do we need to
    # adjust umask to ensure filesystem permissions?
    try:
        os.mkdir(envdir)
    except OSError, e:
        if e.errno <> errno.EEXIST: raise
        # already exists
    # Create the lock file so no other process can open the environment.
    # This is required in order to work around the Berkeley lock
    # exhaustion problem (i.e. we do our own application level locks
    # rather than rely on Berkeley's finite page locks).
    lockfile = LockFile(os.path.join(envdir, '.lock'))
    try:
        # Create, initialize, and open the environment
        env = db.DBEnv()
        if config.logdir is not None:
            env.set_lg_dir(config.logdir)
        gbytes, bytes = divmod(config.cachesize, GBYTES)
        env.set_cachesize(gbytes, bytes)
        env.open(envdir,
                 db.DB_CREATE          # create underlying files as necessary
                 | db.DB_RECOVER       # run normal recovery before opening
                 | db.DB_INIT_MPOOL    # initialize shared memory buffer pool
                 | db.DB_INIT_TXN      # initialize transaction subsystem
                 | db.DB_THREAD        # we use the env from multiple threads
                 )
    except:
        lockfile.close()
        raise
    return env, lockfile



def cleanup(envdir):
    """Remove the entire environment directory for a Berkeley storage."""
    try:
        shutil.rmtree(envdir)
    except OSError, e:
        if e.errno <> errno.ENOENT:
            raise



class _WorkThread(threading.Thread):
    NAME = 'worker'

    def __init__(self, storage, event, checkinterval):
        threading.Thread.__init__(self)
        self._storage = storage
        self._event = event
        self._interval = checkinterval
        # Bookkeeping.  _nextcheck is useful as a non-public interface aiding
        # testing.  See test_autopack.py.
        self._stop = False
        self._nextcheck = checkinterval
        # We don't want these threads to hold up process exit.  That could
        # lead to corrupt databases, but recovery should ultimately save us.
        self.setDaemon(True)

    def run(self):
        name = self.NAME
        self._storage.log('%s thread started', name)
        while not self._stop:
            now = time.time()
            if now >= self._nextcheck:
                self._storage.log('running %s', name)
                self._dowork()
                # Recalculate `now' because _dowork() could have taken a
                # while.  time.time() can be expensive, but oh well.
                self._nextcheck = time.time() + self._interval
            # Block w/ timeout on the shutdown event.
            self._event.wait(self._interval)
            self._stop = self._event.isSet()
        self._storage.log('%s thread finished', name)

    def _dowork(self):
        pass



class _Checkpoint(_WorkThread):
    NAME = 'checkpointing'

    def _dowork(self):
        self._storage.docheckpoint()
