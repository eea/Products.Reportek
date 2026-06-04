import transaction

from Products.PythonScripts.PythonScript import PythonScript

# DRY_RUN = True
DRY_RUN = False

fixed = []
errors = []
found = 0

orig_setstate = PythonScript.__setstate__


def decode_body(value):
    if not isinstance(value, bytes):
        return value

    for enc in ("utf-8", "latin-1"):
        try:
            return value.decode(enc)
        except UnicodeDecodeError:
            pass

    return value.decode("utf-8", "replace")


def patched_setstate(self, state):
    had_bytes = False

    if isinstance(state, dict):
        state = state.copy()

        for key in ("body", "_body"):
            value = state.get(key)
            if isinstance(value, bytes):
                state[key] = decode_body(value)
                had_bytes = True

    result = orig_setstate(self, state)

    if had_bytes:
        self._v_had_broken_bytes_body = True

    return result


PythonScript.__setstate__ = patched_setstate


def walk(container, path="/"):
    global found

    try:
        ids = container.objectIds()
    except Exception as e:
        errors.append((path, "cannot list children", repr(e)))
        return

    for id in ids:
        p = path.rstrip("/") + "/" + id

        try:
            obj = container._getOb(id)
        except Exception as e:
            errors.append((p, "cannot load object", repr(e)))
            continue

        try:
            mt = getattr(obj, "meta_type", None)
        except Exception as e:
            errors.append((p, "cannot read meta_type", repr(e)))
            continue

        if mt == "Script (Python)":
            found += 1

            try:
                recovered = getattr(obj, "_v_had_broken_bytes_body", False)

                body = getattr(obj, "_body", None)
                if isinstance(body, bytes):
                    obj._body = decode_body(body)
                    recovered = True

                if recovered:
                    if obj._body and not obj._body.endswith("\n"):
                        obj._body += "\n"

                    obj._compile()

                    if not DRY_RUN:
                        obj._p_changed = True

                    fixed.append(p)

            except Exception as e:
                errors.append((p, "cannot fix/recompile PythonScript", repr(e)))

        try:
            has_children = hasattr(obj, "objectIds")
        except Exception:
            has_children = False

        if has_children:
            walk(obj, p)


walk(app)

print("")
print("Found Python Scripts:", found)
print("Fixed/recovered candidates:", len(fixed))
print("Errors:", len(errors))
print("DRY_RUN:", DRY_RUN)
print("")

for p in fixed:
    print("FIX:", p)

print("")
for path, reason, detail in errors:
    print("%s :: %s :: %r" % (path, reason, detail))

if DRY_RUN:
    transaction.abort()
    print("")
    print("Dry run only. No changes committed.")
else:
    transaction.commit()
    print("")
    print("Committed recovered Python Scripts.")
