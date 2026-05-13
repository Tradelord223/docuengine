import unittest

from docuengine.render_checks import (
    build_blackdetect_command,
    build_ffprobe_command,
    build_loudnorm_command,
    parse_blackdetect_events,
    parse_loudnorm_summary,
)


class RenderCheckTests(unittest.TestCase):
    def test_builds_ffprobe_command_for_machine_readable_media_info(self):
        self.assertEqual(
            build_ffprobe_command("/tmp/render.mp4"),
            [
                "ffprobe",
                "-v",
                "error",
                "-show_format",
                "-show_streams",
                "-print_format",
                "json",
                "/tmp/render.mp4",
            ],
        )

    def test_builds_blackdetect_and_loudnorm_commands(self):
        self.assertIn("blackdetect=d=0.5:pix_th=0.1", build_blackdetect_command("/tmp/render.mp4"))
        self.assertIn("loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json", build_loudnorm_command("/tmp/render.mp4"))

    def test_parses_blackdetect_events_from_ffmpeg_logs(self):
        log = "[blackdetect @ 0x1] black_start:0 black_end:1.24 black_duration:1.24\n"

        events = parse_blackdetect_events(log)

        self.assertEqual(events, [{"start": 0.0, "end": 1.24, "duration": 1.24}])

    def test_parses_loudnorm_json_summary_embedded_in_logs(self):
        log = """
        frame=  120 fps=0.0
        {
          "input_i" : "-18.23",
          "input_tp" : "-2.31",
          "input_lra" : "7.10",
          "input_thresh" : "-28.50"
        }
        """

        summary = parse_loudnorm_summary(log)

        self.assertEqual(summary["input_i"], -18.23)
        self.assertEqual(summary["input_lra"], 7.10)


if __name__ == "__main__":
    unittest.main()
