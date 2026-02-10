import { useState, useRef, useEffect, KeyboardEvent } from "react";

interface Agent {
  name: string;
  role: string;
  avatar_emoji: string;
}

interface Props {
  value: string;
  onChange: (value: string) => void;
  onSend: () => void;
  agents: Agent[];
  placeholder?: string;
  disabled?: boolean;
}

export function MentionInput({
  value,
  onChange,
  onSend,
  agents,
  placeholder,
  disabled,
}: Props) {
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [suggestions, setSuggestions] = useState<Agent[]>([]);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [mentionStart, setMentionStart] = useState<number | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Parse current input to find @mention being typed
  useEffect(() => {
    const textarea = textareaRef.current;
    if (!textarea) return;

    const cursorPos = textarea.selectionStart;
    const textBeforeCursor = value.slice(0, cursorPos);
    const lastAtIndex = textBeforeCursor.lastIndexOf("@");

    if (lastAtIndex === -1 || textBeforeCursor.slice(lastAtIndex).includes(" ")) {
      setShowSuggestions(false);
      return;
    }

    const query = textBeforeCursor.slice(lastAtIndex + 1).toLowerCase();
    const filtered = agents.filter(
      (a) =>
        a.name.toLowerCase().startsWith(query) ||
        a.role.toLowerCase().includes(query)
    );

    if (filtered.length > 0 && query.length > 0) {
      setSuggestions(filtered);
      setMentionStart(lastAtIndex);
      setShowSuggestions(true);
      setSelectedIndex(0);
    } else {
      setShowSuggestions(false);
    }
  }, [value, agents]);

  const insertMention = (agent: Agent) => {
    if (mentionStart === null) return;

    const textarea = textareaRef.current;
    if (!textarea) return;

    const cursorPos = textarea.selectionStart;
    const before = value.slice(0, mentionStart);
    const after = value.slice(cursorPos);
    const newValue = `${before}@${agent.name} ${after}`;

    onChange(newValue);
    setShowSuggestions(false);

    // Move cursor after mention
    setTimeout(() => {
      const newCursorPos = mentionStart + agent.name.length + 2;
      textarea.setSelectionRange(newCursorPos, newCursorPos);
      textarea.focus();
    }, 0);
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (showSuggestions) {
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setSelectedIndex((i) => (i + 1) % suggestions.length);
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setSelectedIndex((i) => (i - 1 + suggestions.length) % suggestions.length);
      } else if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        insertMention(suggestions[selectedIndex]);
      } else if (e.key === "Escape") {
        setShowSuggestions(false);
      }
    } else if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      onSend();
    }
  };

  // Highlight @mentions in the text
  const renderHighlightedText = () => {
    const parts = value.split(/(@\w+)/g);
    return parts.map((part, i) => {
      if (part.startsWith("@")) {
        const agentName = part.slice(1);
        const agent = agents.find((a) => a.name.toLowerCase() === agentName.toLowerCase());
        return (
          <span key={i} className="mention-highlight">
            {part}
          </span>
        );
      }
      return part;
    });
  };

  return (
    <div className="mention-input-container">
      <textarea
        ref={textareaRef}
        className="mention-input"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        disabled={disabled}
        rows={1}
      />

      {showSuggestions && (
        <div className="mention-suggestions">
          {suggestions.map((agent, i) => (
            <button
              key={agent.name}
              className={`mention-suggestion ${i === selectedIndex ? "selected" : ""}`}
              onClick={() => insertMention(agent)}
              onMouseEnter={() => setSelectedIndex(i)}
            >
              <span className="suggestion-emoji">{agent.avatar_emoji}</span>
              <div className="suggestion-details">
                <div className="suggestion-name">{agent.name}</div>
                <div className="suggestion-role">{agent.role}</div>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
