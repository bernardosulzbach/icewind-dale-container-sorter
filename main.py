import argparse
import zlib

INPUT_FILENAME_OPTION = 'input-filename'
AREA_OPTION = 'area'
SORT_OPTION = 'sort'
EMPTY_CONTAINER_NAME = '<Empty>'
ITEM_SIZE = 0x0010 + 0x0004


class EndOfFileException(Exception):
    pass


def parse_unsigned(data_bytes):
    return int.from_bytes(data_bytes, byteorder='little', signed=False)


def read_unsigned(handle, size):
    read_bytes = handle.read(size)
    if len(read_bytes) != size:
        raise EndOfFileException
    return parse_unsigned(read_bytes)


def write_unsigned(handle, value, size):
    handle.write(value.to_bytes(size, byteorder='little', signed=False))


def parse_string(string_bytes):
    result = string_bytes.decode('ascii')
    result = result.rstrip('\x00')
    return result


def read_string(handle, size):
    return parse_string(handle.read(size))


class Actor:
    def __init__(self, name):
        self.name = name


def parse_actor(actor_bytes):
    return Actor(parse_string(actor_bytes[0:32]))


class Item:
    def __init__(self, resource_reference):
        self.resource_reference = resource_reference


def parse_item(item_bytes):
    return Item(parse_string(item_bytes[0:8]))


class Container:
    def __init__(self, name, first_item_index, item_count):
        self.name = name
        self.first_item_index = first_item_index
        self.item_count = item_count


def parse_container(container_bytes):
    container_name = parse_string(container_bytes[0:32])
    if not container_name:
        container_name = EMPTY_CONTAINER_NAME
    first_item_index = parse_unsigned(container_bytes[0x0040:0x0044])
    item_count = parse_unsigned(container_bytes[0x0044:0x0048])
    return Container(container_name, first_item_index, item_count)


class Area:
    def __init__(self, area_bytes: bytes):
        assert parse_string(area_bytes[0:4]) == 'AREA'
        assert parse_string(area_bytes[4:8]) == 'V1.0'
        self.bytes = area_bytes
        self.actors = self.parse_actors()
        self.items = self.parse_items()
        self.containers = self.parse_containers()

    def parse_actors(self):
        offset_of_actors = parse_unsigned(self.bytes[0x0054:0x0058])
        count_of_actors = parse_unsigned(self.bytes[0x0058:0x005a])
        actor_size = 0x0090 + 0x0080
        actors = []
        for i in range(count_of_actors):
            start = offset_of_actors + actor_size * i
            end = offset_of_actors + actor_size * (i + 1)
            actors.append(parse_actor(self.bytes[start:end]))
        return actors

    def parse_items(self):
        count_of_items = parse_unsigned(self.bytes[0x0076:0x0078])
        offset_of_items = parse_unsigned(self.bytes[0x0078:0x007C])
        items = []
        for i in range(count_of_items):
            start = offset_of_items + ITEM_SIZE * i
            end = offset_of_items + ITEM_SIZE * (i + 1)
            items.append(parse_item(self.bytes[start:end]))
        return items

    def parse_containers(self):
        offset_of_containers = parse_unsigned(self.bytes[0x0070:0x0074])
        count_of_containers = parse_unsigned(self.bytes[0x0074:0x0076])
        container_size = 0x0088 + 0x0038
        containers = []
        for i in range(count_of_containers):
            start = offset_of_containers + container_size * i
            end = offset_of_containers + container_size * (i + 1)
            containers.append(parse_container(self.bytes[start:end]))
        return containers

    def print_summary(self):
        print('Actors:')
        for actor in self.actors:
            print(2 * ' ' + actor.name)
        print('Containers:')
        for container in self.containers:
            print(2 * ' ' + container.name)
            for i in range(container.first_item_index, container.first_item_index + container.item_count):
                print(4 * ' ' + self.items[i].resource_reference)

    def get_item_byte_index(self, item_index):
        # TODO: remove these duplicated constants.
        count_of_items = parse_unsigned(self.bytes[0x0076:0x0078])
        if item_index >= count_of_items:
            raise
        offset_of_items = parse_unsigned(self.bytes[0x0078:0x007C])
        return offset_of_items + ITEM_SIZE * item_index

    def sort_containers(self):
        for container in self.containers:
            if container.item_count == 0:
                continue
            indexed_items = []
            for i in range(container.first_item_index, container.first_item_index + container.item_count):
                indexed_items.append((self.items[i].resource_reference, i))
            indexed_items.sort()
            byte_array = bytearray(self.bytes)
            for i in range(container.first_item_index, container.first_item_index + container.item_count):
                j = i - container.first_item_index
                i_index = self.get_item_byte_index(i)
                j_index = self.get_item_byte_index(indexed_items[j][1])
                byte_array[i_index:i_index + ITEM_SIZE] = self.bytes[j_index:j_index + ITEM_SIZE]
            self.bytes = bytes(byte_array)
        self.items = self.parse_items()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(INPUT_FILENAME_OPTION)
    parser.add_argument('--' + AREA_OPTION)
    parser.add_argument('--' + SORT_OPTION, action='store_true')

    arguments = vars(parser.parse_args())
    area_option = arguments[AREA_OPTION] if AREA_OPTION in arguments else None
    sort_containers = arguments[SORT_OPTION]
    sorted_area = None
    with open(arguments[INPUT_FILENAME_OPTION], 'rb') as file_handle:
        save_version = read_string(file_handle, 8)
        assert save_version == 'SAV V1.0'
        while True:
            try:
                filename = read_string(file_handle, read_unsigned(file_handle, 4))
            except EndOfFileException:
                break
            if area_option is None:
                print('{}'.format(filename))
            uncompressed_data_length = read_unsigned(file_handle, 4)
            compressed_data_length = read_unsigned(file_handle, 4)
            if filename == area_option:
                print('{}'.format(filename))
                compressed_data = file_handle.read(compressed_data_length)
                area_file_bytes = zlib.decompress(compressed_data)
                assert len(area_file_bytes) == uncompressed_data_length
                area = Area(area_file_bytes)
                area.print_summary()
                if sort_containers:
                    area.sort_containers()
                    area.print_summary()
                    sorted_area = area
            else:
                file_handle.seek(compressed_data_length, 1)
    if sorted_area is not None:
        with open('OUTPUT.SAV', 'wb') as output_file_handle:
            with open(arguments[INPUT_FILENAME_OPTION], 'rb') as file_handle:
                output_file_handle.write(file_handle.read(8))
                # No need to assert anything, we have done so already.
                while True:
                    try:
                        filename_size = read_unsigned(file_handle, 4)
                        filename = read_string(file_handle, filename_size)
                        write_unsigned(output_file_handle, filename_size, 4)
                        output_file_handle.write(bytes(filename + '\0', 'ascii'))
                    except EndOfFileException:
                        break
                    uncompressed_data_length = read_unsigned(file_handle, 4)
                    write_unsigned(output_file_handle, uncompressed_data_length, 4)
                    compressed_data_length = read_unsigned(file_handle, 4)
                    compressed_data = file_handle.read(compressed_data_length)
                    if filename == area_option:
                        compressed_data = zlib.compress(sorted_area.bytes)
                        write_unsigned(output_file_handle, len(compressed_data), 4)
                        output_file_handle.write(compressed_data)
                    else:
                        write_unsigned(output_file_handle, compressed_data_length, 4)
                        output_file_handle.write(compressed_data)


if __name__ == '__main__':
    main()
