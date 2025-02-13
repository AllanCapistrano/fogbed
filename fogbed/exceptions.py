class ContainerAlreadyExists(Exception):
    pass

class ContainerNotFound(Exception):
    pass

class NotEnoughResourcesAvailable(Exception):
    pass

class ResourceModelNotFound(Exception):
    pass

class VirtualInstanceAlreadyExists(Exception):
    pass

class VirtualInstanceNotFound(Exception):
    def __init__(self, name: str) -> None:
        super().__init__(f'Datacenter {name} not found.')
    