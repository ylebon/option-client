import time
import pyautogui

from autobahn.twisted.wamp import ApplicationSession, ApplicationRunner
from twisted.internet.defer import inlineCallbacks
from logbook import Logger, StreamHandler
from docopt import docopt
import traceback

import sys

usage = """OptionClient.

Usage:
  option_client.py [--loglevel=<loglevel>] [--call=<call>] [--put=<put>] [--router=<router>]
  option_client.py (-h | --help)
  option_client.py --version

Options:
  -h --help                       Show this screen.
  -r --router=<router>            Set router [default: router.tradingexp-pro.3c9dbdd7.svc.dockerapp.io:8080]
  -c --call=<call>                Set the call coord [default: 1219:525]
  -p --put=<put>                  Set the put coord [default: 1219:645]
  -l --loglevel=<loglevel>        Set log level [default: INFO]
  --version                       Show version.
"""

SCREENWIDTH, SCREENHEIGHT = pyautogui.size()


class BinaryStrategy(object):
    def __init__(self):
        self._log = Logger('binary strategy')
        self._position = False

    def execute(self, instrument, metrics, comment):
        # put (113, 144, 179, 255)
        t = time.time()
        seconds = t % 60
        if not self._position and comment == 'down' and seconds:
            self._log.info('Put signal @ {}'.format(seconds))
            self._position = True
            return 'put'
        elif not self._position and comment == 'up' and seconds:
            self._log.info('Call signal at {}'.format(seconds))
            self._position = True
            return 'call'
        else:
            return


class OptionClientRunner(ApplicationSession):
    def __init__(self, config):
        ApplicationSession.__init__(self, config)
        self._log = Logger('option client')
        self._call_coord = self.config.extra['call_coord']
        self._put_coord = self.config.extra['put_coord']
        self._strategy = BinaryStrategy()
        self._gui = None
        self._call_coord_x = None
        self._call_coord_y = None
        self._put_coord_x = None
        self._put_coord_y = None

    @inlineCallbacks
    def onJoin(self, details):
        self._log.info('joined crossbar.')
        self._call_coord_x, self._call_coord_y = [int(x) for x in self._call_coord.split(':')]
        self._put_coord_x, self._put_coord_y = [int(x) for x in self._put_coord.split(':')]

        @inlineCallbacks
        def receive_event(instrument, metrics, comment):
            """
            Receive prices
            :param event:
            :return:
            """
            self._log.info('received new data {0}: {1}'.format(instrument, metrics))
            signal = self._strategy.execute(instrument, metrics, comment)
            if signal == 'call' and instrument == 'eur_usd':
                self.click_call()
            elif signal == 'put' and instrument == 'eur_usd':
                self.click_put()
            yield

        try:
            yield self.subscribe(receive_event, 'trading.option')
        except:
            traceback.print_exc()
            self.log.error('could not subscribe to event `{}'.format('trading.option'))

    def click_call(self):
        self._log.info('click call')
        pyautogui.click(x=self._call_coord_x, y=self._call_coord_y, clicks=2, button='left')

    def click_put(self):
        self._log.info('click put')
        pyautogui.click(x=self._put_coord_x, y=self._put_coord_y, clicks=2, button='left')


def main(router, call_coord, put_coord, loglevel='INFO'):
    runner = ApplicationRunner(url=u"ws://{0}/ws".format(router), realm=u"realm1",
                               extra={'call_coord': call_coord, 'put_coord': put_coord, 'loglevel': loglevel})
    runner.run(OptionClientRunner)


if __name__ == '__main__':
    arguments = docopt(usage, version='0.0.1')
    with StreamHandler(sys.stdout, level=arguments['--loglevel']):
        main(arguments['--router'], arguments['--call'], arguments['--put'], loglevel=arguments['--loglevel'])
