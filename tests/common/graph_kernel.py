from akg import composite
import os

os.environ["MS_DEV_DUMP_IR"] = "on"
os.environ["MS_DEV_DUMP_CODE"] = "on"

FusedMatMulReshapeTranspose = {
    "composite": True,
    "composite_graph": "1652.1652",
    "compute_capability": "7.5",
    "id": 0,
    "input_desc": [
        [
            {
                "data_type": "float16",
                "format": "DefaultFormat",
                "shape": [
                    1024,
                    1024
                ],
                "tensor_name": "input_1"
            }
        ],
        [
            {
                "data_type": "float16",
                "format": "DefaultFormat",
                "shape": [
                    12288,
                    1024
                ],
                "tensor_name": "input_0"
            }
        ]
    ],
    "op": "Fused_MatMul_Reshape_Transpose_split_10362174774785390160",
    "op_desc": [
        {
            "attr": [
                {
                    "data_type": "str",
                    "name": "right_format",
                    "value": "DefaultFormat"
                },
                {
                    "data_type": "bool",
                    "name": "transpose_x2",
                    "value": True
                },
                {
                    "data_type": "bool",
                    "name": "transpose_b",
                    "value": True
                },
                {
                    "data_type": "str",
                    "name": "left_format",
                    "value": "DefaultFormat"
                },
                {
                    "data_type": "bool",
                    "name": "transpose_a",
                    "value": False
                },
                {
                    "data_type": "bool",
                    "name": "Akg",
                    "value": True
                },
                {
                    "data_type": "bool",
                    "name": "transpose_x1",
                    "value": False
                },
                {
                    "data_type": "str",
                    "name": "dst_type",
                    "value": "float16"
                }
            ],
            "impl_path": "",
            "input_desc": [
                [
                    {
                        "data_type": "float16",
                        "format": "DefaultFormat",
                        "name": "input_0",
                        "shape": [
                            12288,
                            1024
                        ],
                        "tensor_name": "input_0"
                    }
                ],
                [
                    {
                        "data_type": "float16",
                        "format": "DefaultFormat",
                        "name": "input_1",
                        "shape": [
                            1024,
                            1024
                        ],
                        "tensor_name": "input_1"
                    }
                ]
            ],
            "name": "MatMul",
            "output_desc": [
                {
                    "data_type": "float16",
                    "format": "DefaultFormat",
                    "name": "output_0",
                    "shape": [
                        12288,
                        1024
                    ],
                    "tensor_name": "output_0_0"
                }
            ]
        },
        {
            "attr": [
                {
                    "data_type": "listInt",
                    "name": "shape",
                    "value": [
                        96,
                        128,
                        4,
                        256
                    ]
                }
            ],
            "impl_path": "",
            "input_desc": [
                [
                    {
                        "data_type": "float16",
                        "format": "DefaultFormat",
                        "name": "input_0",
                        "shape": [
                            12288,
                            1024
                        ],
                        "tensor_name": "output_0_0"
                    }
                ]
            ],
            "name": "Reshape",
            "output_desc": [
                {
                    "data_type": "float16",
                    "format": "DefaultFormat",
                    "name": "output_0",
                    "shape": [
                        96,
                        128,
                        4,
                        256
                    ],
                    "tensor_name": "output_0_1"
                }
            ]
        },
        {
            "attr": [
                {
                    "data_type": "listInt",
                    "name": "perm",
                    "value": [
                        0,
                        2,
                        1,
                        3
                    ]
                }
            ],
            "impl_path": "",
            "input_desc": [
                [
                    {
                        "data_type": "float16",
                        "format": "DefaultFormat",
                        "name": "input_0",
                        "shape": [
                            96,
                            128,
                            4,
                            256
                        ],
                        "tensor_name": "output_0_1"
                    }
                ]
            ],
            "name": "Transpose",
            "output_desc": [
                {
                    "data_type": "float16",
                    "format": "DefaultFormat",
                    "name": "output_0",
                    "shape": [
                        96,
                        4,
                        128,
                        256
                    ],
                    "tensor_name": "output_0_2"
                }
            ]
        }
    ],
    "output_desc": [
        {
            "data_type": "float16",
            "format": "DefaultFormat",
            "shape": [
                96,
                4,
                128,
                256
            ],
            "tensor_name": "output_0_2"
        }
    ],
    "platform": "AKG",
    "process": "cuda"
}

FusedMatMulAdd = {
    "composite": True,
    "composite_graph": "1652.1652",
    "compute_capability": "7.5",
    "id": 0,
    "input_desc": [
        [
            {
                "data_type": "float16",
                "format": "DefaultFormat",
                "shape": [1024],
                "tensor_name": "input_2"
            }
        ],
        [
            {
                "data_type": "float16",
                "format": "DefaultFormat",
                "shape": [
                    1024,
                    1024
                ],
                "tensor_name": "input_1"
            }
        ],
        [
            {
                "data_type": "float16",
                "format": "DefaultFormat",
                "shape": [
                    12288,
                    1024
                ],
                "tensor_name": "input_0"
            }
        ]
    ],
    "op": "Fused_MatMul_Add_split_10362174774785390160",
    "op_desc": [
        {
            "attr": [
                {
                    "data_type": "str",
                    "name": "right_format",
                    "value": "DefaultFormat"
                },
                {
                    "data_type": "bool",
                    "name": "transpose_x2",
                    "value": True
                },
                {
                    "data_type": "bool",
                    "name": "transpose_b",
                    "value": True
                },
                {
                    "data_type": "str",
                    "name": "left_format",
                    "value": "DefaultFormat"
                },
                {
                    "data_type": "bool",
                    "name": "transpose_a",
                    "value": False
                },
                {
                    "data_type": "bool",
                    "name": "Akg",
                    "value": True
                },
                {
                    "data_type": "bool",
                    "name": "transpose_x1",
                    "value": False
                },
                {
                    "data_type": "str",
                    "name": "dst_type",
                    "value": "float16"
                }
            ],
            "impl_path": "",
            "input_desc": [
                [
                    {
                        "data_type": "float16",
                        "format": "DefaultFormat",
                        "name": "input_0",
                        "shape": [
                            12288,
                            1024
                        ],
                        "tensor_name": "input_0"
                    }
                ],
                [
                    {
                        "data_type": "float16",
                        "format": "DefaultFormat",
                        "name": "input_1",
                        "shape": [
                            1024,
                            1024
                        ],
                        "tensor_name": "input_1"
                    }
                ]
            ],
            "name": "MatMul",
            "output_desc": [
                {
                    "data_type": "float16",
                    "format": "DefaultFormat",
                    "name": "output_0",
                    "shape": [
                        12288,
                        1024
                    ],
                    "tensor_name": "output_0_0"
                }
            ]
        },
        {
            "attr": [
                {
                    "name": "enable_atomic_add",
                    "value": True
                },
            ],
            "impl_path":"",
            "input_desc":   [
                [
                    {
                        "data_type":"float16",
                        "format":"DefaultFormat",
                        "name":"input_0",
                        "shape": [
                            12288,
                            1024
                        ],
                        "tensor_name":"output_0_0"
                    }
                ],
                [
                    {
                        "data_type":"float16",
                        "format":"DefaultFormat",
                        "name":"input_1",
                        "shape": [1024],
                        "tensor_name":"input_2"
                    }
                ]
            ],
            "name":"Add",
            "output_desc": [
                {
                    "data_type":"float16",
                    "format":"DefaultFormat",
                    "name":"output_0",
                    "shape": [
                        12288,
                        1024
                    ],
                    "tensor_name":"output_0_2"
                }
            ]        
        }
    ],
    "output_desc": [
        {
            "data_type": "float16",
            "format": "DefaultFormat",
            "shape": [
                12288,
                1024
            ],
            "tensor_name": "output_0_2"
        }
    ],
    "platform": "AKG",
    "process": "cuda"
}

composite.build(FusedMatMulAdd)