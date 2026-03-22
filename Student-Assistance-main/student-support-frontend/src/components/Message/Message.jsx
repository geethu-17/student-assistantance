import "./Message.css";

function Message({ text, sender }) {

  return (
    <div className={`message ${sender}`}>
      {text}
    </div>
  );

}

export default Message;