import json
import time
import logging
import random
import datetime as dt

class RXMetadataModification:
    def __init__(self, rx_adjust):
        self.min_rssi = -120
        self.max_rssi = -90  # valid to 50 miles via FSPL filter
        self.max_snr = 1.9
        self.min_snr = -9.9
        self.tmst_offset = 0
        self.rx_adjust = rx_adjust
        self.logger = logging.getLogger('RXMeta')

    def modify_rxpk(self, rxpk, src_mac=None, dest_mac=None):
        old_snr, old_rssi, old_ts = rxpk['lsnr'], rxpk['rssi'], rxpk['tmst']
        rxpk['rssi'] += self.rx_adjust
        rxpk['lsnr'] = round(rxpk['lsnr'] + random.randint(-15, 10) * 0.1, 1)  # randomize snr +/- 1dB in 0.1dB increments

        rxpk['rssi'] = min(self.max_rssi, max(self.min_rssi, rxpk['rssi']))
        rxpk['lsnr'] = min(self.max_snr,  max(self.min_snr,  rxpk['lsnr']))

        ts_dt = dt.datetime.utcnow()
        gps_valid = False
        if 'time' in rxpk:
            ts_str = rxpk['time']
            if ts_str[-1] == 'Z':
                ts_str = ts_str[:-1]
                ts_dt = dt.datetime.fromisoformat(ts_str)
            if abs((ts_dt - dt.datetime.utcnow()).total_seconds()) > 1.5:
                ts_dt = dt.datetime.utcnow()
            else:
                gps_valid = True

        ts_midnight = dt.datetime(year=ts_dt.year, month=ts_dt.month, day=ts_dt.day, hour=0, minute=0, second=0, microsecond=0)
        elapsed_us = int((ts_dt-ts_midnight).total_seconds() * 1e6)
        elapsed_us_u32 = elapsed_us % 2**32

        if src_mac != dest_mac:
            rxpk['tmst'] = (elapsed_us_u32 + self.tmst_offset) % 2**32
        else:
            tmst_offset = (rxpk['tmst'] - elapsed_us_u32 + 2**32) % 2**32
            self.tmst_offset = tmst_offset
        self.logger.debug(f"modified packet from GW {src_mac[-8:]} to vGW {dest_mac[-8:]}, rssi:{old_rssi}->{rxpk['rssi']}, lsnr:{old_snr}->{rxpk['lsnr']:.1f}, tmst:{old_ts}->{rxpk['tmst']} {'GPS SYNC' if gps_valid else ''}")
        return rxpk