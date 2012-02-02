import exceptions

class UserExistsWarning(exceptions.Warning):
    pass


class ClientExistsWarning(exceptions.Warning):
    pass


class AssociationExistsWarning(exceptions.Warning):
    pass


class ConfidentailError(exceptions.Exception):
    pass
