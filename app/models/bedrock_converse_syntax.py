
'''
BedrockRuntime.Client.converse(**kwargs)
Request Syntax
'''
response = client.converse(
    modelId='string',
    messages=[
        {
            'role': 'user'|'assistant',
            'content': [
                {
                    'text': 'string',
                    'image': {
                        'format': 'png'|'jpeg'|'gif'|'webp',
                        'source': {
                            'bytes': b'bytes'
                        }
                    },
                    'document': {
                        'format': 'pdf'|'csv'|'doc'|'docx'|'xls'|'xlsx'|'html'|'txt'|'md',
                        'name': 'string',
                        'source': {
                            'bytes': b'bytes'
                        }
                    },
                    'video': {
                        'format': 'mkv'|'mov'|'mp4'|'webm'|'flv'|'mpeg'|'mpg'|'wmv'|'three_gp',
                        'source': {
                            'bytes': b'bytes',
                            's3Location': {
                                'uri': 'string',
                                'bucketOwner': 'string'
                            }
                        }
                    },
                    'toolUse': {
                        'toolUseId': 'string',
                        'name': 'string',
                        'input': {...}|[...]|123|123.4|'string'|True|None
                    },
                    'toolResult': {
                        'toolUseId': 'string',
                        'content': [
                            {
                                'json': {...}|[...]|123|123.4|'string'|True|None,
                                'text': 'string',
                                'image': {
                                    'format': 'png'|'jpeg'|'gif'|'webp',
                                    'source': {
                                        'bytes': b'bytes'
                                    }
                                },
                                'document': {
                                    'format': 'pdf'|'csv'|'doc'|'docx'|'xls'|'xlsx'|'html'|'txt'|'md',
                                    'name': 'string',
                                    'source': {
                                        'bytes': b'bytes'
                                    }
                                },
                                'video': {
                                    'format': 'mkv'|'mov'|'mp4'|'webm'|'flv'|'mpeg'|'mpg'|'wmv'|'three_gp',
                                    'source': {
                                        'bytes': b'bytes',
                                        's3Location': {
                                            'uri': 'string',
                                            'bucketOwner': 'string'
                                        }
                                    }
                                }
                            },
                        ],
                        'status': 'success'|'error'
                    },
                    'guardContent': {
                        'text': {
                            'text': 'string',
                            'qualifiers': [
                                'grounding_source'|'query'|'guard_content',
                            ]
                        },
                        'image': {
                            'format': 'png'|'jpeg',
                            'source': {
                                'bytes': b'bytes'
                            }
                        }
                    }
                },
            ]
        },
    ],
    system=[
        {
            'text': 'string',
            'guardContent': {
                'text': {
                    'text': 'string',
                    'qualifiers': [
                        'grounding_source'|'query'|'guard_content',
                    ]
                },
                'image': {
                    'format': 'png'|'jpeg',
                    'source': {
                        'bytes': b'bytes'
                    }
                }
            }
        },
    ],
    inferenceConfig={
        'maxTokens': 123,
        'temperature': ...,
        'topP': ...,
        'stopSequences': [
            'string',
        ]
    },
    toolConfig={
        'tools': [
            {
                'toolSpec': {
                    'name': 'string',
                    'description': 'string',
                    'inputSchema': {
                        'json': {...}|[...]|123|123.4|'string'|True|None
                    }
                }
            },
        ],
        'toolChoice': {
            'auto': {}
            ,
            'any': {}
            ,
            'tool': {
                'name': 'string'
            }
        }
    },
    guardrailConfig={
        'guardrailIdentifier': 'string',
        'guardrailVersion': 'string',
        'trace': 'enabled'|'disabled'
    },
    additionalModelRequestFields={...}|[...]|123|123.4|'string'|True|None,
    promptVariables={
        'string': {
            'text': 'string'
        }
    },
    additionalModelResponseFieldPaths=[
        'string',
    ],
    requestMetadata={
        'string': 'string'
    },
    performanceConfig={
        'latency': 'standard'|'optimized'
    }
)


'''
BedrockRuntime.Client.converse(**kwargs)
Response Syntax
'''

{
    'output': {
        'message': {
            'role': 'user'|'assistant',
            'content': [
                {
                    'text': 'string',
                    'image': {
                        'format': 'png'|'jpeg'|'gif'|'webp',
                        'source': {
                            'bytes': b'bytes'
                        }
                    },
                    'document': {
                        'format': 'pdf'|'csv'|'doc'|'docx'|'xls'|'xlsx'|'html'|'txt'|'md',
                        'name': 'string',
                        'source': {
                            'bytes': b'bytes'
                        }
                    },
                    'video': {
                        'format': 'mkv'|'mov'|'mp4'|'webm'|'flv'|'mpeg'|'mpg'|'wmv'|'three_gp',
                        'source': {
                            'bytes': b'bytes',
                            's3Location': {
                                'uri': 'string',
                                'bucketOwner': 'string'
                            }
                        }
                    },
                    'toolUse': {
                        'toolUseId': 'string',
                        'name': 'string',
                        'input': {...}|[...]|123|123.4|'string'|True|None
                    },
                    'toolResult': {
                        'toolUseId': 'string',
                        'content': [
                            {
                                'json': {...}|[...]|123|123.4|'string'|True|None,
                                'text': 'string',
                                'image': {
                                    'format': 'png'|'jpeg'|'gif'|'webp',
                                    'source': {
                                        'bytes': b'bytes'
                                    }
                                },
                                'document': {
                                    'format': 'pdf'|'csv'|'doc'|'docx'|'xls'|'xlsx'|'html'|'txt'|'md',
                                    'name': 'string',
                                    'source': {
                                        'bytes': b'bytes'
                                    }
                                },
                                'video': {
                                    'format': 'mkv'|'mov'|'mp4'|'webm'|'flv'|'mpeg'|'mpg'|'wmv'|'three_gp',
                                    'source': {
                                        'bytes': b'bytes',
                                        's3Location': {
                                            'uri': 'string',
                                            'bucketOwner': 'string'
                                        }
                                    }
                                }
                            },
                        ],
                        'status': 'success'|'error'
                    },
                    'guardContent': {
                        'text': {
                            'text': 'string',
                            'qualifiers': [
                                'grounding_source'|'query'|'guard_content',
                            ]
                        },
                        'image': {
                            'format': 'png'|'jpeg',
                            'source': {
                                'bytes': b'bytes'
                            }
                        }
                    }
                },
            ]
        }
    },
    'stopReason': 'end_turn'|'tool_use'|'max_tokens'|'stop_sequence'|'guardrail_intervened'|'content_filtered',
    'usage': {
        'inputTokens': 123,
        'outputTokens': 123,
        'totalTokens': 123
    },
    'metrics': {
        'latencyMs': 123
    },
    'additionalModelResponseFields': {...}|[...]|123|123.4|'string'|True|None,
    'trace': {
        'guardrail': {
            'modelOutput': [
                'string',
            ],
            'inputAssessment': {
                'string': {
                    'topicPolicy': {
                        'topics': [
                            {
                                'name': 'string',
                                'type': 'DENY',
                                'action': 'BLOCKED'
                            },
                        ]
                    },
                    'contentPolicy': {
                        'filters': [
                            {
                                'type': 'INSULTS'|'HATE'|'SEXUAL'|'VIOLENCE'|'MISCONDUCT'|'PROMPT_ATTACK',
                                'confidence': 'NONE'|'LOW'|'MEDIUM'|'HIGH',
                                'filterStrength': 'NONE'|'LOW'|'MEDIUM'|'HIGH',
                                'action': 'BLOCKED'
                            },
                        ]
                    },
                    'wordPolicy': {
                        'customWords': [
                            {
                                'match': 'string',
                                'action': 'BLOCKED'
                            },
                        ],
                        'managedWordLists': [
                            {
                                'match': 'string',
                                'type': 'PROFANITY',
                                'action': 'BLOCKED'
                            },
                        ]
                    },
                    'sensitiveInformationPolicy': {
                        'piiEntities': [
                            {
                                'match': 'string',
                                'type': 'ADDRESS'|'AGE'|'AWS_ACCESS_KEY'|'AWS_SECRET_KEY'|'CA_HEALTH_NUMBER'|'CA_SOCIAL_INSURANCE_NUMBER'|'CREDIT_DEBIT_CARD_CVV'|'CREDIT_DEBIT_CARD_EXPIRY'|'CREDIT_DEBIT_CARD_NUMBER'|'DRIVER_ID'|'EMAIL'|'INTERNATIONAL_BANK_ACCOUNT_NUMBER'|'IP_ADDRESS'|'LICENSE_PLATE'|'MAC_ADDRESS'|'NAME'|'PASSWORD'|'PHONE'|'PIN'|'SWIFT_CODE'|'UK_NATIONAL_HEALTH_SERVICE_NUMBER'|'UK_NATIONAL_INSURANCE_NUMBER'|'UK_UNIQUE_TAXPAYER_REFERENCE_NUMBER'|'URL'|'USERNAME'|'US_BANK_ACCOUNT_NUMBER'|'US_BANK_ROUTING_NUMBER'|'US_INDIVIDUAL_TAX_IDENTIFICATION_NUMBER'|'US_PASSPORT_NUMBER'|'US_SOCIAL_SECURITY_NUMBER'|'VEHICLE_IDENTIFICATION_NUMBER',
                                'action': 'ANONYMIZED'|'BLOCKED'
                            },
                        ],
                        'regexes': [
                            {
                                'name': 'string',
                                'match': 'string',
                                'regex': 'string',
                                'action': 'ANONYMIZED'|'BLOCKED'
                            },
                        ]
                    },
                    'contextualGroundingPolicy': {
                        'filters': [
                            {
                                'type': 'GROUNDING'|'RELEVANCE',
                                'threshold': 123.0,
                                'score': 123.0,
                                'action': 'BLOCKED'|'NONE'
                            },
                        ]
                    },
                    'invocationMetrics': {
                        'guardrailProcessingLatency': 123,
                        'usage': {
                            'topicPolicyUnits': 123,
                            'contentPolicyUnits': 123,
                            'wordPolicyUnits': 123,
                            'sensitiveInformationPolicyUnits': 123,
                            'sensitiveInformationPolicyFreeUnits': 123,
                            'contextualGroundingPolicyUnits': 123
                        },
                        'guardrailCoverage': {
                            'textCharacters': {
                                'guarded': 123,
                                'total': 123
                            },
                            'images': {
                                'guarded': 123,
                                'total': 123
                            }
                        }
                    }
                }
            },
            'outputAssessments': {
                'string': [
                    {
                        'topicPolicy': {
                            'topics': [
                                {
                                    'name': 'string',
                                    'type': 'DENY',
                                    'action': 'BLOCKED'
                                },
                            ]
                        },
                        'contentPolicy': {
                            'filters': [
                                {
                                    'type': 'INSULTS'|'HATE'|'SEXUAL'|'VIOLENCE'|'MISCONDUCT'|'PROMPT_ATTACK',
                                    'confidence': 'NONE'|'LOW'|'MEDIUM'|'HIGH',
                                    'filterStrength': 'NONE'|'LOW'|'MEDIUM'|'HIGH',
                                    'action': 'BLOCKED'
                                },
                            ]
                        },
                        'wordPolicy': {
                            'customWords': [
                                {
                                    'match': 'string',
                                    'action': 'BLOCKED'
                                },
                            ],
                            'managedWordLists': [
                                {
                                    'match': 'string',
                                    'type': 'PROFANITY',
                                    'action': 'BLOCKED'
                                },
                            ]
                        },
                        'sensitiveInformationPolicy': {
                            'piiEntities': [
                                {
                                    'match': 'string',
                                    'type': 'ADDRESS'|'AGE'|'AWS_ACCESS_KEY'|'AWS_SECRET_KEY'|'CA_HEALTH_NUMBER'|'CA_SOCIAL_INSURANCE_NUMBER'|'CREDIT_DEBIT_CARD_CVV'|'CREDIT_DEBIT_CARD_EXPIRY'|'CREDIT_DEBIT_CARD_NUMBER'|'DRIVER_ID'|'EMAIL'|'INTERNATIONAL_BANK_ACCOUNT_NUMBER'|'IP_ADDRESS'|'LICENSE_PLATE'|'MAC_ADDRESS'|'NAME'|'PASSWORD'|'PHONE'|'PIN'|'SWIFT_CODE'|'UK_NATIONAL_HEALTH_SERVICE_NUMBER'|'UK_NATIONAL_INSURANCE_NUMBER'|'UK_UNIQUE_TAXPAYER_REFERENCE_NUMBER'|'URL'|'USERNAME'|'US_BANK_ACCOUNT_NUMBER'|'US_BANK_ROUTING_NUMBER'|'US_INDIVIDUAL_TAX_IDENTIFICATION_NUMBER'|'US_PASSPORT_NUMBER'|'US_SOCIAL_SECURITY_NUMBER'|'VEHICLE_IDENTIFICATION_NUMBER',
                                    'action': 'ANONYMIZED'|'BLOCKED'
                                },
                            ],
                            'regexes': [
                                {
                                    'name': 'string',
                                    'match': 'string',
                                    'regex': 'string',
                                    'action': 'ANONYMIZED'|'BLOCKED'
                                },
                            ]
                        },
                        'contextualGroundingPolicy': {
                            'filters': [
                                {
                                    'type': 'GROUNDING'|'RELEVANCE',
                                    'threshold': 123.0,
                                    'score': 123.0,
                                    'action': 'BLOCKED'|'NONE'
                                },
                            ]
                        },
                        'invocationMetrics': {
                            'guardrailProcessingLatency': 123,
                            'usage': {
                                'topicPolicyUnits': 123,
                                'contentPolicyUnits': 123,
                                'wordPolicyUnits': 123,
                                'sensitiveInformationPolicyUnits': 123,
                                'sensitiveInformationPolicyFreeUnits': 123,
                                'contextualGroundingPolicyUnits': 123
                            },
                            'guardrailCoverage': {
                                'textCharacters': {
                                    'guarded': 123,
                                    'total': 123
                                },
                                'images': {
                                    'guarded': 123,
                                    'total': 123
                                }
                            }
                        }
                    },
                ]
            }
        },
        'promptRouter': {
            'invokedModelId': 'string'
        }
    },
    'performanceConfig': {
        'latency': 'standard'|'optimized'
    }
}