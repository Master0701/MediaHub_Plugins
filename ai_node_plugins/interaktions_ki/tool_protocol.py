"""Shared, dependency-free validation for the supported function-tool protocol.

Schemas outside this deliberately bounded subset are rejected, never ignored.
No tool is executed here. Historical calls need not be in the current tool list.
"""
import copy
import json
import math
import re

NAME = re.compile(r"^[A-Za-z0-9_-]{1,128}$")
TYPES = {"object", "array", "string", "integer", "number", "boolean", "null"}
KEYS = {"type", "properties", "required", "additionalProperties", "items", "enum",
        "const", "description", "title", "default", "examples", "minimum", "maximum",
        "exclusiveMinimum", "exclusiveMaximum", "minLength", "maxLength", "minItems",
        "maxItems", "anyOf", "oneOf", "allOf"}


def loads(value):
    def bad_constant(_):
        raise ValueError("Nicht-endliche JSON-Zahl")
    def pairs(items):
        result = {}
        for key, item in items:
            if key in result:
                raise ValueError("Doppelter JSON-Schluessel")
            result[key] = item
        return result
    def number(text):
        result = float(text)
        if not math.isfinite(result):
            raise ValueError("Nicht-endliche JSON-Zahl")
        return result
    return json.loads(value, parse_constant=bad_constant, parse_float=number, object_pairs_hook=pairs)


def check_schema(schema, depth=0):
    if depth > 16 or not isinstance(schema, dict) or set(schema) - KEYS:
        raise ValueError("Nicht unterstuetztes Werkzeug-Schema")
    kinds = schema.get("type", [])
    kinds = [kinds] if isinstance(kinds, str) else kinds
    if not isinstance(kinds, list) or any(not isinstance(k, str) or k not in TYPES for k in kinds):
        raise ValueError("Ungueltiger Schema-Typ")
    props = schema.get("properties", {})
    required = schema.get("required", [])
    if not isinstance(props, dict) or not isinstance(required, list) or any(not isinstance(k, str) for k in required):
        raise ValueError("Ungueltige Schema-Felder")
    for sub in props.values():
        check_schema(sub, depth + 1)
    extra = schema.get("additionalProperties", True)
    if isinstance(extra, dict):
        check_schema(extra, depth + 1)
    elif not isinstance(extra, bool):
        raise ValueError("Ungueltiges additionalProperties")
    if "items" in schema:
        check_schema(schema["items"], depth + 1)
    if "enum" in schema and (not isinstance(schema["enum"], list) or not schema["enum"]):
        raise ValueError("Ungueltiges enum")
    for key in ("anyOf", "oneOf", "allOf"):
        if key in schema:
            if not isinstance(schema[key], list) or not schema[key]:
                raise ValueError("Ungueltige Schema-Kombination")
            for sub in schema[key]:
                check_schema(sub, depth + 1)
    for key in ("minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum",
                "minLength", "maxLength", "minItems", "maxItems"):
        if key in schema:
            v = schema[key]
            if type(v) not in (int, float) or not math.isfinite(v):
                raise ValueError("Ungueltige Schema-Grenze")
            if key.endswith(("Length", "Items")) and (type(v) is not int or v < 0):
                raise ValueError("Ungueltige Schema-Laenge")


def equal(a, b):
    # JSON booleans must not compare equal to numbers (Python: True == 1).
    if isinstance(a, bool) or isinstance(b, bool):
        return type(a) is type(b) and a == b
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(equal(a[k], b[k]) for k in a)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(equal(x, y) for x, y in zip(a, b))
    return a == b


def validate(value, schema):
    kinds = schema.get("type", [])
    kinds = [kinds] if isinstance(kinds, str) else kinds
    number = type(value) is int or (type(value) is float and math.isfinite(value))
    matches = {"object": isinstance(value, dict), "array": isinstance(value, list),
               "string": isinstance(value, str), "boolean": type(value) is bool,
               "null": value is None, "number": number,
               "integer": number and int(value) == value}
    if kinds and not any(matches[k] for k in kinds):
        raise ValueError("Werkzeugargument hat falschen Datentyp")
    if "enum" in schema and not any(equal(value, v) for v in schema["enum"]):
        raise ValueError("Werkzeugargument ausserhalb enum")
    if "const" in schema and not equal(value, schema["const"]):
        raise ValueError("Werkzeugargument verletzt const")
    for key in ("anyOf", "oneOf", "allOf"):
        if key in schema:
            count = 0
            for sub in schema[key]:
                try:
                    validate(value, sub)
                    count += 1
                except ValueError:
                    pass
            if (key == "anyOf" and count == 0 or key == "oneOf" and count != 1
                    or key == "allOf" and count != len(schema[key])):
                raise ValueError("Werkzeugargument verletzt Schema-Kombination")
    if isinstance(value, dict):
        if any(k not in value for k in schema.get("required", [])):
            raise ValueError("Tool-Pflichtargumente fehlen")
        props = schema.get("properties", {})
        extra = schema.get("additionalProperties", True)
        for key, item in value.items():
            if key in props:
                validate(item, props[key])
            elif extra is False:
                raise ValueError("Unerlaubte Tool-Argumente")
            elif isinstance(extra, dict):
                validate(item, extra)
    if isinstance(value, list) and "items" in schema:
        for item in value:
            validate(item, schema["items"])
    for low, high, size in (("minLength", "maxLength", len(value) if isinstance(value, str) else None),
                            ("minItems", "maxItems", len(value) if isinstance(value, list) else None)):
        if size is not None and (size < schema.get(low, 0) or size > schema.get(high, float("inf"))):
            raise ValueError("Werkzeugargument verletzt Laengengrenze")
    if number:
        if (value < schema.get("minimum", -math.inf) or value > schema.get("maximum", math.inf)
                or value <= schema.get("exclusiveMinimum", -math.inf)
                or value >= schema.get("exclusiveMaximum", math.inf)):
            raise ValueError("Werkzeugargument verletzt Zahlengrenze")


def options(payload):
    mode = payload.get("tool_calling_mode", "native")
    if mode not in ("native", "json_compat"):
        raise ValueError("tool_calling_mode muss native oder json_compat sein")
    if payload.get("parallel_tool_calls", False) is not False:
        raise ValueError("Parallele Werkzeugaufrufe werden noch nicht unterstuetzt")
    tools = payload.get("tools", [])
    if not isinstance(tools, list) or len(tools) > 32:
        raise ValueError("Ungueltige Tool-Liste")
    definitions = {}
    for tool in tools:
        if not isinstance(tool, dict) or tool.get("type") != "function":
            raise ValueError("Nur function-Tools werden unterstuetzt")
        fn = tool.get("function")
        if not isinstance(fn, dict) or not isinstance(fn.get("name"), str) or not NAME.fullmatch(fn["name"]):
            raise ValueError("Ungueltiger Tool-Name")
        if fn["name"] in definitions:
            raise ValueError("Doppelter Tool-Name")
        check_schema(fn.get("parameters", {"type": "object"}))
        definitions[fn["name"]] = fn
    choice = payload.get("tool_choice", "auto" if tools else "none")
    forced = None
    if isinstance(choice, dict):
        fn = choice.get("function")
        if choice.get("type") != "function" or not isinstance(fn, dict):
            raise ValueError("Ungueltige tool_choice")
        forced = fn.get("name")
        if not isinstance(forced, str) or forced not in definitions:
            raise ValueError("Erzwungenes Tool nicht vorhanden")
    elif not isinstance(choice, str) or choice not in ("none", "auto", "required"):
        raise ValueError("Ungueltige tool_choice")
    if choice == "required" and not tools:
        raise ValueError("required ohne Tools")
    return mode, tools, definitions, choice, forced


def call_arguments(call):
    if not isinstance(call, dict) or call.get("type") != "function":
        raise ValueError("Ungueltiger Tool-Aufruf")
    fn = call.get("function")
    if (not isinstance(fn, dict) or not isinstance(fn.get("name"), str)
            or not NAME.fullmatch(fn["name"]) or not isinstance(fn.get("arguments"), str)
            or len(fn["arguments"]) > 50000 or not isinstance(call.get("id"), str) or not call["id"]):
        raise ValueError("Ungueltige Tool-Aufrufdaten")
    args = loads(fn["arguments"])
    if not isinstance(args, dict):
        raise ValueError("Tool-Argumente muessen ein Objekt sein")
    return fn["name"], args


def messages(items):
    if not isinstance(items, list) or not 1 <= len(items) <= 40:
        raise ValueError("messages muss 1 bis 40 Eintraege enthalten")
    pending, seen = set(), set()
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("Ungueltige Nachricht")
        role, content = item.get("role"), item.get("content")
        if pending and role != "tool":
            raise ValueError("Tool-Ergebnisse fehlen")
        if role == "assistant" and item.get("tool_calls"):
            calls = item["tool_calls"]
            if not isinstance(calls, list) or not 1 <= len(calls) <= 16:
                raise ValueError("Ungueltige tool_calls")
            if content is not None and (not isinstance(content, str) or len(content) > 50000):
                raise ValueError("Ungueltiger Nachrichteninhalt")
            for call in calls:
                call_arguments(call)
                cid = call["id"]
                if cid in seen:
                    raise ValueError("Doppelte tool_call_id")
                pending.add(cid)
                seen.add(cid)
        elif role == "tool":
            cid = item.get("tool_call_id")
            if not isinstance(cid, str) or cid not in pending or not isinstance(content, str) or len(content) > 50000:
                raise ValueError("Ungueltiges Tool-Ergebnis")
            pending.remove(cid)
        elif role not in ("system", "user", "assistant") or not isinstance(content, str) or not content.strip() or len(content) > 50000:
            raise ValueError("Ungueltige Nachrichtenrolle oder Inhalt")
        elif item.get("tool_calls") or "tool_call_id" in item:
            raise ValueError("Werkzeugdaten an falscher Nachrichtenrolle")
    if pending:
        raise ValueError("Tool-Ergebnisse fehlen")
    return copy.deepcopy(items)


def response(message, finish_reason, definitions, choice, forced):
    if not isinstance(message, dict) or message.get("role", "assistant") != "assistant":
        raise ValueError("Ungueltige KI-Antwort")
    calls = message.get("tool_calls", [])
    if not isinstance(calls, list) or len(calls) > 1:
        raise ValueError("Ungueltige oder parallele Tool-Aufrufe")
    content = message.get("content")
    if content is not None and not isinstance(content, str):
        raise ValueError("Ungueltiger Antworttext")
    if calls:
        if choice == "none" or finish_reason != "tool_calls":
            raise ValueError("Verbotener oder unvollstaendiger Tool-Aufruf")
        name, args = call_arguments(calls[0])
        if name not in definitions or (forced and name != forced):
            raise ValueError("KI lieferte unbekanntes oder falsches Werkzeug")
        validate(args, definitions[name].get("parameters", {"type": "object"}))
    elif forced or choice == "required":
        raise ValueError("KI hat keinen gueltigen verpflichtenden Tool-Aufruf erzeugt")
    elif finish_reason not in ("stop", "length") or not isinstance(content, str) or not content.strip():
        raise ValueError("llama-server lieferte keinen Antworttext oder ungueltigen Abschluss")
    return copy.deepcopy(message)
