#
# Copyright (c) 2019 Nordic Semiconductor ASA
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met:
#
#   1. Redistributions of source code must retain the above copyright notice, this
#   list of conditions and the following disclaimer.
#
#   2. Redistributions in binary form must reproduce the above copyright notice, this
#   list of conditions and the following disclaimer in the documentation and/or
#   other materials provided with the distribution.
#
#   3. Neither the name of Nordic Semiconductor ASA nor the names of other
#   contributors to this software may be used to endorse or promote products
#   derived from this software without specific prior written permission.
#
#   4. This software must only be used in or with a processor manufactured by Nordic
#   Semiconductor ASA, or in or with a processor manufactured by a third party that
#   is used in combination with a processor manufactured by Nordic Semiconductor.
#
#   5. Any software provided in binary or object form under this license must not be
#   reverse engineered, decompiled, modified and/or disassembled.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
# ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
from driver_setup import Settings, setup_adapter
import logging
logger = logging.getLogger(__name__)


import random
import string
import unittest
from queue import Queue

import xmlrunner

from pc_ble_driver_py.ble_driver import BLEAdvData, BLEOpts, BLEOptGapChMap
from pc_ble_driver_py.exceptions import NordicSemiException
from pc_ble_driver_py.observers import BLEDriverObserver, BLEAdapterObserver


class Central(BLEDriverObserver, BLEAdapterObserver):
    def __init__(self, adapter):
        self.adapter = adapter
        logger.info("Central adapter is %d", self.adapter.driver.rpc_adapter.internal)
        self.conn_q = Queue()
        self.dl_q = Queue()
        self.adapter.observer_register(self)
        self.adapter.driver.observer_register(self)
        self.conn_handle = None

    def start(self, connect_with, requested_dl):
        self.connect_with = connect_with
        logger.info("scan_start, trying to find %s", self.connect_with)
        self.adapter.driver.ble_gap_scan_start()
        self.conn_handle = self.conn_q.get(timeout=5)
        # self.adapter.data_length_update(self.conn_handle, requested_dl)
        opt = BLEOptGapChMap()
        opt.conn_handle = self.conn_handle
        breakpoint()
        opt_retval = self.adapter.driver.ble_opt_get(BLEOpts.gap_ch_map, opt)
        print(opt_retval)

    def stop(self):
        if self.conn_handle:
            self.adapter.driver.ble_gap_disconnect(self.conn_handle)

    def on_gap_evt_adv_report(
        self, ble_driver, conn_handle, peer_addr, rssi, adv_type, adv_data
    ):
        if BLEAdvData.Types.complete_local_name in adv_data.records:
            dev_name_list = adv_data.records[BLEAdvData.Types.complete_local_name]

        elif BLEAdvData.Types.short_local_name in adv_data.records:
            dev_name_list = adv_data.records[BLEAdvData.Types.short_local_name]
        else:
            return

        dev_name = "".join(chr(e) for e in dev_name_list)

        if dev_name == self.connect_with:
            address_string = "".join("{0:02X}".format(b) for b in peer_addr.addr)
            logger.info(
                "Trying to connect to peripheral advertising as %s, address: 0x%s",
                dev_name,
                address_string,
            )

            self.adapter.connect(peer_addr, tag=Settings.CFG_TAG)

    def on_gap_evt_connected(
        self, ble_driver, conn_handle, peer_addr, role, conn_params
    ):
        self.conn_q.put(conn_handle)

    # This event is handled by BLEAdapter. Included here for test inspection only.
    def on_gap_evt_data_length_update(
        self, ble_driver, conn_handle, data_length_params
    ):
        self.dl_q.put(data_length_params.max_tx_octets)


class Peripheral(BLEDriverObserver, BLEAdapterObserver):
    def __init__(self, adapter):
        self.adapter = adapter
        logger.info(
            "Peripheral adapter is %d",
            self.adapter.driver.rpc_adapter.internal,
        )
        self.conn_q = Queue()
        self.dl_req_q = Queue()
        self.dl_q = Queue()
        self.adapter.observer_register(self)
        self.adapter.driver.observer_register(self)

    def start(self, adv_name):
        adv_data = BLEAdvData(complete_local_name=adv_name)
        self.adapter.driver.ble_gap_adv_data_set(adv_data)
        self.adapter.driver.ble_gap_adv_start(tag=Settings.CFG_TAG)

    def on_gap_evt_connected(
        self, ble_driver, conn_handle, peer_addr, role, conn_params
    ):
        self.conn_q.put(conn_handle)

    # This event is handled by BLEAdapter. Included here for test inspection only.
    def on_gap_evt_data_length_update_request(
        self, ble_driver, conn_handle, data_length_params
    ):
        self.dl_req_q.put(data_length_params.max_tx_octets)

    # This event is handled by BLEAdapter. Included here for test inspection only.
    def on_gap_evt_data_length_update(
        self, ble_driver, conn_handle, data_length_params
    ):
        self.dl_q.put(data_length_params.max_tx_octets)


class DataLength(unittest.TestCase):
    def setUp(self):
        settings = Settings.current()

        settings.mtu = 250
        settings.event_length = 5

        central = setup_adapter(
            settings.serial_ports[0],
            False,
            settings.baud_rate,
            settings.retransmission_interval,
            settings.response_timeout,
            settings.driver_log_level,
        )

        self.central = Central(central)

        peripheral = setup_adapter(
            settings.serial_ports[1],
            False,
            settings.baud_rate,
            settings.retransmission_interval,
            settings.response_timeout,
            settings.driver_log_level,
        )

        # Advertising name used by peripheral and central
        # to find peripheral and connect with it
        self.adv_name = "".join(
            random.choice(string.ascii_uppercase + string.digits) for _ in range(20)
        )
        self.peripheral = Peripheral(peripheral)

    def test_data_length_150(self):
        requested_data_length = 150

        self.peripheral.start(self.adv_name)
        self.central.start(self.adv_name, requested_data_length)

        dl_req_periph = self.peripheral.dl_req_q.get(timeout=5)
        self.assertEqual(dl_req_periph, requested_data_length)

        dl_periph = self.peripheral.dl_q.get(timeout=5)
        self.assertEqual(dl_periph, requested_data_length)

        dl_central = self.central.dl_q.get(timeout=5)
        self.assertEqual(dl_central, requested_data_length)

        self.central.stop()

    def xtest_data_length_requiring_increased_event_length(self):
        requested_data_length = 251

        self.peripheral.start(self.adv_name)
        self.central.start(self.adv_name, requested_data_length)

        dl_req_periph = self.peripheral.dl_req_q.get(timeout=5)
        self.assertEqual(dl_req_periph, requested_data_length)

        dl_periph = self.peripheral.dl_q.get(timeout=5)
        self.assertEqual(dl_periph, requested_data_length)

        dl_central = self.central.dl_q.get(timeout=5)
        self.assertEqual(dl_central, requested_data_length)

        self.central.stop()

    def xtest_data_length_too_large(self):
        requested_data_length = 252

        self.peripheral.start(self.adv_name)
        with self.assertRaises(NordicSemiException):
            self.central.start(self.adv_name, requested_data_length)

        self.central.stop()

    def tearDown(self):
        self.central.adapter.close()
        self.peripheral.adapter.close()


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)


if __name__ == "__main__":
    logging.basicConfig(
        level=Settings.current().log_level,
        format="%(asctime)s [%(thread)d/%(threadName)s] %(message)s",
    )
    unittest.main(
        testRunner=xmlrunner.XMLTestRunner(
            output=Settings.current().test_output_directory
        ),
        argv=Settings.clean_args(),
    )
