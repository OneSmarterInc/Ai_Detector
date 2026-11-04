import styles from "./inspector.module.css";
/** Map module-local class names, including conditional class lists. */
export function classNames(value) {
  return value
    .split(/\s+/)
    .map((name) => styles[name] || "")
    .filter(Boolean)
    .join(" ");
}
