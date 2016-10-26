"""
Redis RDB backup script.
Written in Python 2.7
"""
# -*- coding: utf-8 -*-

from time import sleep
from datetime import datetime, timedelta

import argparse
import redis
import sys
import os
import shutil
import hashlib

__author__ = 'Luke.The.Coder'


def file_md5(filename, blocksize=2**20):
    f = open(filename)
    md5 = hashlib.md5()
    while True:
        data = f.read(blocksize)
        if not data:
            break
        md5.update(data)
    f.close()
    return md5.digest()


def checksum_compare(src, dst):
    """
    """
    assert(os.path.isfile(src) and os.path.isfile(dst))
    return file_md5(src) == file_md5(dst)


def bgsave_and_wait(r, timeout=timedelta(seconds=60)):
    assert (isinstance(r, redis.StrictRedis))

    bgsave_begin = datetime.now()

    t0 = r.lastsave()
    if r.bgsave():
        while True:
            if r.lastsave() != t0:
                break
            if datetime.now() - bgsave_begin > timeout:
                return 'timeout'
            sleep(1)
        return 'ok'
    else:
        return 'failed'


def rdb_path(r):
    """
    Get&return redis config `dbfilename`
    """
    assert (isinstance(r, redis.StrictRedis))
    d = r.config_get('dir')
    dbfilename = r.config_get('dbfilename')
    return '%s/%s' % (d['dir'], dbfilename['dbfilename'])


def aof_path(r, aof_filename):
    """
    Get&return redis config `appendfilename`
    """
    assert (isinstance(r, redis.StrictRedis))
    d = r.config_get('dir')
    return os.path.join(d['dir'], aof_filename)


def copy_data_file(data_file, backup_dir, backup_filename, port, file_type):
    """
    Copies and renames the redis data file to backup dir, compare checksums
    when finished.

    The final backup name is:
    data_file_mtime.strftime(backup_filename) + "(port_%d)" % port

    Returns backup file path when the copy was success and passed the checksum
    check. otherwise, return None
    """
    df_mtime = os.path.getmtime(data_file)
    df_mtime = datetime.fromtimestamp(df_mtime).strftime(backup_filename)
    backup_filename = '%s(port_%d).%s' % (df_mtime, port, file_type)
    backup_path = os.path.join(backup_dir, backup_filename)

    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
    elif not os.path.isdir(backup_dir):
        sys.stderr.write('backupdir: %s is not a directory.\n' % backup_dir)
        return None
    elif os.path.exists(backup_path):
        sys.stderr.write('backupfile: %s already exists.\n' % backup_path)
        return None

    shutil.copy2(data_file, backup_path)

    if not checksum_compare(data_file, backup_path):
        sys.stderr.write('failed to copy dbfile %s, checksum compare failed.'
                         % data_file)
        return None
    print 'backup', backup_path, 'created.', \
        os.path.getsize(backup_path), 'bytes, checksum ok!'
    return backup_path


def copy_rdb(rdb, backup_dir, backup_filename, port):
    """
    Copies and renames the rdb file to backup dir, compare checksums when
    finished.

    Returns backup file path when the copy was success and passed the checksum
    check. otherwise, return None
    """
    return copy_data_file(rdb, backup_dir, backup_filename, port, 'rdb')


def copy_aof(aof, backup_dir, backup_filename, port):
    """
    Copies and renames the aof file to backup dir, compare checksums when
    finished.

    Returns backup file path when the copy was success and passed the checksum
    check. otherwise, return None
    """
    return copy_data_file(aof, backup_dir, backup_filename, port, 'aof')


def clean_backup_dir(backup_dir, max_backups, port, file_type):
    """
    Removes oldest backups if the total number of backups exceeds max_backups
    """
    file_suffix = '(port_%d).%s' % (port, file_type)
    files = [f for f in os.listdir(backup_dir) if f.endswith(file_suffix)]
    n_files = len(files)
    if n_files <= max_backups:
        return

    print 'number of backups(%d) exceeds limit(%d), deleting old backups.'\
        % (n_files, max_backups)

    files_time = []
    for filename in files:
        fp = '%s/%s' % (backup_dir, filename)
        # some time error
        files_time.append((fp, os.path.getmtime(fp)))
    files_time.sort(key=lambda x: x[1])

    for fp in files_time[:n_files - max_backups]:
        print 'delete', fp[0]
        os.remove(fp[0])

    files = [f for f in os.listdir(backup_dir) if f.endswith(file_suffix)]
    assert(len(files) == max_backups)


def clean_rdb_backup(backup_dir, max_backups, port):
    """
    Removes oldest rdb backups if the total number of backups exceeds
    max_backups
    """
    return clean_backup_dir(backup_dir, max_backups, port, 'rdb')


def clean_aof_backup(backup_dir, max_backups, port):
    """
    Removes oldest aof backups if the total number of backups exceeds
    max_backups
    """
    return clean_backup_dir(backup_dir, max_backups, port, 'aof')


def main():
    # Ensures that there is only one instance of this script is running.
    # code from
    # http://stackoverflow.com/questions/380870/python-single-instance-of-program
    # from tendo import singleton
    # me = singleton.SingleInstance()

    # Setup command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('-backup_dir', type=str, dest='backup_dir',
                        help='backup directory', default='./backups')
    parser.add_argument('-backup_filename', type=str, dest='backup_filename',
                        help='', default='redis_dump_%Y-%m-%d_%H%M%S')
    parser.add_argument('-redis_port', type=int, dest='redis_port',
                        help='redis port', default=6379)
    parser.add_argument('-max_backups', type=int, dest='max_backups',
                        help='maximum number of backups to keep', default=10)
    parser.add_argument('-bgsave_timeout', type=int, dest='bgsave_timeout',
                        help='bgsave timeout in seconds', default=60)
    parser.add_argument('-with_aof', dest="with_aof", help='enable backup aof',
                        action="store_true")
    parser.add_argument('-aof_filename', dest="aof_filename",
                        default='appendonly.aof', help='aof filename')

    # Parse command line arguments
    args = parser.parse_args()

    args.backup_dir = os.path.abspath(args.backup_dir)

    st = datetime.now()

    backup_dir = args.backup_dir
    backup_filename = args.backup_filename
    max_backups = args.max_backups
    redis_port = args.redis_port
    bgsave_timeout = args.bgsave_timeout
    with_aof = args.with_aof
    aof_filename = args.aof_filename

    print 'backup begin @', st
    print 'backup dir:    \t', backup_dir
    print 'backup file:   \t', backup_filename
    print 'max backups:   \t', max_backups
    print 'redis port:    \t', redis_port
    print 'bgsave timeout:\t', bgsave_timeout, 'seconds'

    # Connect to local redis server
    r = redis.StrictRedis(port=args.redis_port)
    print 'connected to redis server localhost:%d' % args.redis_port

    # Get where redis saves the RDB file
    rdb = rdb_path(r)
    print 'redis rdb file path:', rdb

    if with_aof:
        aof = aof_path(r, aof_filename)
        print 'redis aof file path:', aof

    # Start bgsave and wait for it to finish
    print 'redis bgsave...',
    sys.stdout.flush()
    ret = bgsave_and_wait(r, timeout=timedelta(seconds=args.bgsave_timeout))
    print ret

    if ret != 'ok':
        sys.stderr.write('%s %s\n' % ('backup failed!', datetime.now() - st))
        sys.exit(1)

    print 'stating copy rdb...'
    rdb_bak_path = copy_rdb(rdb, backup_dir, backup_filename, redis_port)
    if not rdb_bak_path:
        sys.stderr.write('%s %s\n' % ('backup failed!', datetime.now() - st))
        sys.exit(1)

    if with_aof:
        print 'stating copy aof...'
        aof_bak_path = copy_aof(aof, backup_dir, backup_filename, redis_port)
        if not aof_bak_path:
            os.remove(rdb_bak_path)
            sys.stderr.write('%s %s\n' % ('backup failed!', datetime.now()-st))
            sys.exit(1)

    clean_rdb_backup(backup_dir, max_backups, redis_port)
    if with_aof:
        clean_aof_backup(backup_dir, max_backups, redis_port)

    print 'backup successful! time cost:', datetime.now() - st

if __name__ == '__main__':
    main()
