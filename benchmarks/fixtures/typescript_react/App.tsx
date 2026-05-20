import React, { useState } from 'react';

interface ButtonProps {
  label: string;
  onClick: () => void;
}

function Button({ label, onClick }: ButtonProps): JSX.Element {
  return <button onClick={onClick}>{label}</button>;
}

function useCounter(initial: number) {
  const [count, setCount] = useState(initial);
  return { count, increment: () => setCount(c => c + 1) };
}

function App(): JSX.Element {
  const { count, increment } = useCounter(0);
  return (
    <div>
      <p>Count: {count}</p>
      <Button label="Increment" onClick={increment} />
    </div>
  );
}

export default App;
