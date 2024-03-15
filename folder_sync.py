__author__ = 'Lukáš Bartůněk'

import os
import sys
import shutil
import logging
import argparse
from filecmp import dircmp
from functools import partial
from ischedule import schedule, run_loop


# creates a logger that prints into log file and stdout
def set_loggers(log_path):
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s')

    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(logging.DEBUG)
    stdout_handler.setFormatter(formatter)

    file_handler = logging.FileHandler(log_path + 'folder_sync.log')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(stdout_handler)

    return logger


# main function comparing and syncing folders, uses recursive
def sync(comp, source, target, logger, path='', identical=1):
    for name in comp.left_only:
        s = source + path + '/' + name
        t = target + path + '/' + name
        if os.path.isdir(s):
            for (dir_path, _, filenames) in os.walk(s):
                for file in filenames:
                    logger.info('File ' + dir_path + '/' + file + ' copied to ' + t + '.')
            shutil.copytree(s, t)
        else:
            shutil.copy2(s, t)
            logger.info('File ' + s + ' copied to ' + t + '.')
    for name in comp.right_only:
        t = target + path + '/' + name
        if os.path.isdir(t):
            for (dir_path, _, filenames) in os.walk(t):
                for file in filenames:
                    logger.info('File ' + dir_path + '/' + file + ' removed from target folder.')
            shutil.rmtree(t)
        else:
            os.remove(t)
            logger.info('File ' + t + ' removed from target folder.')

    for sub_comp in comp.subdirs.keys():
        if not sync(comp.subdirs[sub_comp], source, target, logger, str(path + '/' + sub_comp), identical):
            identical = 0
    if len(comp.left_only) > 0 or len(comp.right_only) > 0 or len(comp.funny_files) > 0:
        identical = 0
    return identical


# support function scheduled to periodically call sync
# checks if arguments are correct and creates target folder if it doesn't exist
def periodic_sync(params):
    arg_list = params[0]
    logger = params[1]

    if not os.path.isdir(arg_list.source):
        logger.error("Source folder doesn't exist.")
        raise FileNotFoundError
    if not os.path.isdir(arg_list.target):
        if arg_list.create_target:
            os.makedirs(arg_list.target)
            logger.info("Target folder created.")
        else:
            logger.error("Target folder doesn't exist.")
            raise FileNotFoundError

    if sync(dircmp(arg_list.source, arg_list.target), arg_list.source, arg_list.target, logger):
        logger.info("Folders are identical. No need for syncing.")
    else:
        logger.info("Syncing of folders completed.")


if __name__ == "__main__":
    # parser for argument setting
    parser = argparse.ArgumentParser(
        description="This script periodically syncs two folders",
        epilog='Lukáš Bartůněk, 2024')
    parser.add_argument('-source',
                        help='Source file used for syncing.', required=True)
    parser.add_argument('-target',
                        help='Target file used for syncing.', required=True)
    parser.add_argument('-log_path', default='',
                        help='Path to logging file.')
    parser.add_argument('-interval',
                        help='Synchronization interval in seconds', required=True)
    parser.add_argument('-create_target', action="store_true",
                        help='Creates the destination folder if it doesn\'t exist.')
    args = parser.parse_args()

    # creates a log file if it doesn't exist
    if os.path.exists(args.log_path + '/folder_sync.log'):
        log = set_loggers(args.log_path)
    else:
        log = set_loggers(args.log_path)
        log.info("Log file created.")

    # first call of the function is immediate
    periodic_sync([args, log])

    # schedules function call every x seconds
    schedule(partial(periodic_sync, [args, log]), interval=float(args.interval))

    try:
        # starts scheduled task
        run_loop()
    except KeyboardInterrupt:
        print("Keyboard interrupt")
    except FileNotFoundError:
        pass
    except Exception as e:
        print(e)
