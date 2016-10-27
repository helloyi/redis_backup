# Redis RDB local backup script
This python script `redis_backup.py` will create local Redis RDB-snapshot backups using the `bgsave` command to a given directory:

0. Issue a `bgsave` command
1. Wait for `bgsave` to finish successfully
2. Copy the newly created RDB file to the backup directory
3. Copy the newly created AOF file to the backup directory when enable aof backup with `-with_aof`
4. Verify MD5 checksum
5. Remove old `.rdb` files if the backup directory is too crowded

## Environment Requirement

0. Python 2.7
1. Python modules: `redis`
2. A redis instance running locally. *You should always `rsync` the local backup directory to other servers to maximize the data safety.*

## Usage
    
      -h, --help                       show this help message and exit
      -backup_dir BACKUP_DIR           backup directory
      -backup_filename BACKUP_FILENAME backup filename format
      -redis_port REDIS_PORT           redis port
      -max_backups MAX_BACKUPS         maximum number of pair(rdb and rof) backups to keep
      -bgsave_timeout BGSAVE_TIMEOUT   bgsave timeout in seconds
      -with_aof                        enable backup aof
      -aof_filename AOF_FILENAME       aof filename

## Running the script
The script can be run with no arguments:

	$ python reids_backup.py
	backup begin @ 2015-03-28 18:30:43.828446
	backup dir:    	/opt/work/RedisBackup/backups
	backup file:   	redis_dump_%Y-%m-%d_%H%M%S
	max backups:   	10
	redis port:    	6379
	bgsave timeout:	60 seconds
	connected to redis server localhost:6379
	redis rdb file path: /opt/src/redis-2.8.19/dump.rdb
	redis bgsave... ok
	backup /opt/work/RedisBackup/backups/redis_dump_2015-03-28_183044(port_6379).rdb created. 18 bytes, checksum ok!
	backup successful! time cost: 0:00:01.005492

    $ python redis_backup.py -backup_dir ~/tmp/data -with_aof
    backup begin @ 2016-10-27 11:49:33.461467
    backup dir:    	/home/helloyi/tmp/data
    backup file:   	redis_dump_%Y-%m-%d_%H%M%S
    max backups:   	10
    redis port:    	6379
    bgsave timeout:	60 seconds
    connected to redis server localhost:6379
    redis rdb file path: /var/lib/redis/dump.rdb
    redis aof file path: /var/lib/redis/appendonly.aof
    redis bgsave... ok
    stating copy rdb...
    backup /home/helloyi/tmp/data/redis_dump_2016-10-27_114933(port_6379).rdb created. 160 bytes, checksum ok!
    stating copy aof...
    backup /home/helloyi/tmp/data/redis_dump_2016-10-27_114354(port_6379).aof created. 490 bytes, checksum ok!
    backup successful! time cost: 0:00:01.003707

    # backup failed when aof not modify!
    $ python redis_backup.py -backup_dir ~/tmp/data -with_aof
    backup begin @ 2016-10-27 11:51:57.456741
    backup dir:    	/home/helloyi/tmp/data
    backup file:   	redis_dump_%Y-%m-%d_%H%M%S
    max backups:   	10
    redis port:    	6379
    bgsave timeout:	60 seconds
    connected to redis server localhost:6379
    redis rdb file path: /var/lib/redis/dump.rdb
    redis aof file path: /var/lib/redis/appendonly.aof
    redis bgsave... ok
    stating copy rdb...
    backup /home/helloyi/tmp/data/redis_dump_2016-10-27_115157(port_6379).rdb created. 160 bytes, checksum ok!
    stating copy aof...
    backupfile: /home/helloyi/tmp/data/redis_dump_2016-10-27_114354(port_6379).aof already exists.
    remove /home/helloyi/tmp/data/redis_dump_2016-10-27_115157(port_6379).rdb
    backup failed! 0:00:01.003626

If everything goes well, this will create a RDB backup file in the `./backups` directory.
