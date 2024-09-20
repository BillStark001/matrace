

import uuid
import base64


def gen_uuid_b64():
  uuid_obj = uuid.uuid4()
  uuid_bytes = uuid_obj.bytes
  b64_encoded = base64.urlsafe_b64encode(
      uuid_bytes).rstrip(b'=').decode('ascii')
  return b64_encoded
