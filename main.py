import argparse
import zlib

INPUT_FILENAME_OPTION = 'input-filename'
AREA_OPTION = 'area'


class EndOfFileException(Exception):
    pass


def parse_unsigned(data_bytes):
    return int.from_bytes(data_bytes, byteorder='little', signed=False)


def read_unsigned_32(handle):
    read_bytes = handle.read(4)
    if len(read_bytes) != 4:
        raise EndOfFileException
    return parse_unsigned(read_bytes)


def read_string(handle, size):
    return parse_string(handle.read(size))


def parse_string(string_bytes):
    result = string_bytes.decode('ascii')
    result = result.rstrip('\x00')
    return result


def parse_actor(actor_bytes):
    print('  {}'.format(parse_string(actor_bytes[0:32])))


def parse_area_file(area_file_bytes):
    assert parse_string(area_file_bytes[0:4]) == 'AREA'
    assert parse_string(area_file_bytes[4:8]) == 'V1.0'

    print('Actors:')
    offset_of_actors = parse_unsigned(area_file_bytes[0x0054:0x0058])
    count_of_actors = parse_unsigned(area_file_bytes[0x0058:0x005a])
    actor_size = 0x0090 + 0x0080
    for i in range(count_of_actors):
        parse_actor(area_file_bytes[offset_of_actors + actor_size * i:offset_of_actors + actor_size * (i + 1)])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(INPUT_FILENAME_OPTION)
    parser.add_argument('--' + AREA_OPTION)

    arguments = vars(parser.parse_args())
    area_option = arguments[AREA_OPTION] if AREA_OPTION in arguments else None

    with open(arguments[INPUT_FILENAME_OPTION], 'rb') as file_handle:
        save_version = read_string(file_handle, 8)
        assert save_version == 'SAV V1.0'
        while True:
            try:
                filename = read_string(file_handle, read_unsigned_32(file_handle))
            except EndOfFileException:
                break
            if area_option is None:
                print('{}'.format(filename))
            uncompressed_data_length = read_unsigned_32(file_handle)
            compressed_data_length = read_unsigned_32(file_handle)
            if filename == area_option:
                print('{}'.format(filename))
                compressed_data = file_handle.read(compressed_data_length)
                area_file_bytes = zlib.decompress(compressed_data)
                parse_area_file(area_file_bytes)
            else:
                file_handle.seek(compressed_data_length, 1)


if __name__ == '__main__':
    main()
