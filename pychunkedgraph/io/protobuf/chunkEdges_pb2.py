# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: chunkEdges.proto

import sys
_b=sys.version_info[0]<3 and (lambda x:x) or (lambda x:x.encode('latin1'))
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import symbol_database as _symbol_database
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor.FileDescriptor(
  name='chunkEdges.proto',
  package='test',
  syntax='proto3',
  serialized_options=None,
  serialized_pb=_b('\n\x10\x63hunkEdges.proto\x12\x04test\"\xc5\x01\n\x05\x45\x64ges\x12%\n\x07inChunk\x18\x04 \x01(\x0b\x32\x14.test.Edges.EdgesDef\x12(\n\ncrossChunk\x18\x05 \x01(\x0b\x32\x14.test.Edges.EdgesDef\x12*\n\x0c\x62\x65tweenChunk\x18\x06 \x01(\x0b\x32\x14.test.Edges.EdgesDef\x1a?\n\x08\x45\x64gesDef\x12\x10\n\x08\x65\x64geList\x18\x01 \x01(\x0c\x12\x12\n\naffinities\x18\x02 \x01(\x0c\x12\r\n\x05\x61reas\x18\x03 \x01(\x0c\x62\x06proto3')
)




_EDGES_EDGESDEF = _descriptor.Descriptor(
  name='EdgesDef',
  full_name='test.Edges.EdgesDef',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='edgeList', full_name='test.Edges.EdgesDef.edgeList', index=0,
      number=1, type=12, cpp_type=9, label=1,
      has_default_value=False, default_value=_b(""),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='affinities', full_name='test.Edges.EdgesDef.affinities', index=1,
      number=2, type=12, cpp_type=9, label=1,
      has_default_value=False, default_value=_b(""),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='areas', full_name='test.Edges.EdgesDef.areas', index=2,
      number=3, type=12, cpp_type=9, label=1,
      has_default_value=False, default_value=_b(""),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=161,
  serialized_end=224,
)

_EDGES = _descriptor.Descriptor(
  name='Edges',
  full_name='test.Edges',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='inChunk', full_name='test.Edges.inChunk', index=0,
      number=4, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='crossChunk', full_name='test.Edges.crossChunk', index=1,
      number=5, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='betweenChunk', full_name='test.Edges.betweenChunk', index=2,
      number=6, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
  ],
  extensions=[
  ],
  nested_types=[_EDGES_EDGESDEF, ],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=27,
  serialized_end=224,
)

_EDGES_EDGESDEF.containing_type = _EDGES
_EDGES.fields_by_name['inChunk'].message_type = _EDGES_EDGESDEF
_EDGES.fields_by_name['crossChunk'].message_type = _EDGES_EDGESDEF
_EDGES.fields_by_name['betweenChunk'].message_type = _EDGES_EDGESDEF
DESCRIPTOR.message_types_by_name['Edges'] = _EDGES
_sym_db.RegisterFileDescriptor(DESCRIPTOR)

Edges = _reflection.GeneratedProtocolMessageType('Edges', (_message.Message,), {

  'EdgesDef' : _reflection.GeneratedProtocolMessageType('EdgesDef', (_message.Message,), {
    'DESCRIPTOR' : _EDGES_EDGESDEF,
    '__module__' : 'chunkEdges_pb2'
    # @@protoc_insertion_point(class_scope:test.Edges.EdgesDef)
    })
  ,
  'DESCRIPTOR' : _EDGES,
  '__module__' : 'chunkEdges_pb2'
  # @@protoc_insertion_point(class_scope:test.Edges)
  })
_sym_db.RegisterMessage(Edges)
_sym_db.RegisterMessage(Edges.EdgesDef)


# @@protoc_insertion_point(module_scope)
