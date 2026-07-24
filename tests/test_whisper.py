import os
import time

import whisper as whisper_lib

from nectar_metrics import whisper as nm_whisper

from tests.utils import TestSender


NOW = int(time.time())


def make_wsp(base, metric_path, points, archives=((10, 30), (60, 60))):
    """Create a whisper file under base for metric_path.

    archives defaults to 10s x 30 points (5 minutes fine) and
    60s x 60 points (1 hour coarse).
    """
    filepath = os.path.join(base, *metric_path.split('.')) + '.wsp'
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    whisper_lib.create(filepath, list(archives), xFilesFactor=0.0)
    whisper_lib.update_many(filepath, points)
    return filepath


def sample_points():
    # One point per 60s across the last ~55 minutes: the newest points
    # land in the fine (10s) archive's 5-minute window, the rest only
    # in the coarse (60s) archive.
    return [
        (ts, float(i)) for i, ts in enumerate(range(NOW - 3300, NOW - 30, 60))
    ]


def test_archive_bands_are_disjoint_and_coarsest_first(tmp_path):
    filepath = make_wsp(str(tmp_path), 'az.zone1.used_vcpus', sample_points())
    info = whisper_lib.info(filepath)
    bands = nm_whisper.archive_bands(info, NOW)
    assert len(bands) == 2
    (coarse, c_from, c_until), (fine, f_from, f_until) = bands
    assert coarse['secondsPerPoint'] == 60
    assert fine['secondsPerPoint'] == 10
    # disjoint and contiguous: coarse band ends where fine begins
    assert c_until == f_from
    assert f_until == NOW
    assert c_from == NOW - 3600
    assert f_from == NOW - 300


def test_send_file_replays_all_bands_chronologically(tmp_path):
    filepath = make_wsp(str(tmp_path), 'az.zone1.used_vcpus', sample_points())
    sender = TestSender()
    count, first_ts, last_ts = nm_whisper.send_file(
        sender, filepath, 'az.zone1.used_vcpus', NOW
    )

    assert count == len(sender.metrics)
    timestamps = [args[2] for args in sender.metrics]
    # chronological, no duplicates
    assert timestamps == sorted(timestamps)
    assert len(timestamps) == len(set(timestamps))
    # both bands are represented: points older than the fine archive's
    # 5-minute retention and points inside it
    assert [ts for ts in timestamps if ts < NOW - 300]
    assert [ts for ts in timestamps if ts >= NOW - 300]
    assert first_ts == timestamps[0]
    assert last_ts == timestamps[-1]
    # every replayed point carries the original metric path
    assert set(args[0] for args in sender.metrics) == {'az.zone1.used_vcpus'}


def test_send_file_respects_limit(tmp_path):
    filepath = make_wsp(str(tmp_path), 'az.zone1.used_vcpus', sample_points())
    sender = TestSender()
    count, _, _ = nm_whisper.send_file(
        sender, filepath, 'az.zone1.used_vcpus', NOW, limit=5
    )
    assert count == 5
    assert len(sender.metrics) == 5


def test_do_report_filters_to_migration_set(tmp_path):
    make_wsp(str(tmp_path), 'az.zone1.used_vcpus', sample_points())
    make_wsp(
        str(tmp_path),
        'az.zone1.domain.unimelb_edu_au.used_vcpus',
        sample_points(),
    )
    make_wsp(str(tmp_path), 'tenant.8ffff.total_volumes', sample_points())
    make_wsp(
        str(tmp_path), 'az.zone1.tenant.8ffff.used_vcpus', sample_points()
    )

    sender = TestSender()
    files, points = nm_whisper.do_report(
        sender, str(tmp_path), nm_whisper.DEFAULT_INCLUDES, NOW
    )
    assert files == 2
    assert points == len(sender.metrics)
    sent_paths = set(args[0] for args in sender.metrics)
    assert sent_paths == {
        'az.zone1.used_vcpus',
        'az.zone1.domain.unimelb_edu_au.used_vcpus',
    }
    assert sender.flushes == 1


def test_do_report_dry_run_sends_nothing(tmp_path):
    make_wsp(str(tmp_path), 'az.zone1.used_vcpus', sample_points())
    sender = TestSender()
    files, points = nm_whisper.do_report(
        sender, str(tmp_path), nm_whisper.DEFAULT_INCLUDES, NOW, dry_run=True
    )
    assert files == 1
    assert points > 0
    assert sender.metrics == []
    assert sender.flushes == 0


def test_glob_does_not_cross_dots():
    regex = nm_whisper.glob_to_regex('az.*.used_vcpus')
    assert regex.match('az.zone1.used_vcpus')
    assert not regex.match('az.zone1.domain.unimelb_edu_au.used_vcpus')
    assert not regex.match('az.zone1.tenant.8ffff.used_vcpus')
    regex = nm_whisper.glob_to_regex('az.*.domain.*.used_vcpus')
    assert regex.match('az.zone1.domain.unimelb_edu_au.used_vcpus')
    assert not regex.match('az.zone1.used_vcpus')
