import logging
from pathlib import Path
import paramiko


class SftpUploader:
    def __init__(
            self,
            host: str,
            username: str,
            private_key: str,
            port: int = 22,
    ):
        self.host = host
        self.port = port
        self.username = username
        self.private_key = private_key

    def upload_file(
            self,
            local_file: str,
            remote_file: str,
    ) -> None:
        local_file = Path(local_file)

        logging.info(
            "Uploading %s to sftp://%s:%s%s",
            local_file,
            self.host,
            self.port,
            remote_file,
        )

        key = paramiko.Ed25519Key.from_private_key_file(
            self.private_key
        )

        transport = paramiko.Transport((self.host, self.port))

        try:
            transport.connect(
                username=self.username,
                pkey=key,
            )

            sftp = paramiko.SFTPClient.from_transport(
                transport
            )

            sftp.put(
                str(local_file),
                remote_file,
            )

            logging.info(
                "Successfully uploaded %s",
                local_file,
            )

        finally:
            transport.close()