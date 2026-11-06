import re
import unicodedata


class RobotRadioUtils:

    @staticmethod
    def sanitize_filename(name: str) -> str:

        name = unicodedata.normalize("NFKD", name)
        name = name.encode("ascii", "ignore").decode("ascii")

        name = re.sub(r"\s+", "_", name)
        name = re.sub(r"[^A-Za-z0-9._-]", "", name)
        name = re.sub(r"_+", "_", name)

        return name.strip("_")
