"""S3 simulado en memoria: suficiente para probar handlers y el almacén sin red ni AWS."""
from io import BytesIO


class NoSuchKey(Exception):
    def __init__(self):
        self.response = {"Error": {"Code": "NoSuchKey"}}


class FakeS3:
    def __init__(self):
        self.objetos = {}

    def put_object(self, Bucket, Key, Body, **kw):
        self.objetos[(Bucket, Key)] = bytes(Body)

    def get_object(self, Bucket, Key):
        if (Bucket, Key) not in self.objetos:
            raise NoSuchKey()
        return {"Body": BytesIO(self.objetos[(Bucket, Key)])}

    def list_objects_v2(self, Bucket, Prefix="", **kw):
        return {"Contents": [{"Key": k} for (b, k) in sorted(self.objetos) if b == Bucket and k.startswith(Prefix)]}

    def delete_object(self, Bucket, Key):
        self.objetos.pop((Bucket, Key), None)

    def llaves(self, bucket):
        return sorted(k for (b, k) in self.objetos if b == bucket)
