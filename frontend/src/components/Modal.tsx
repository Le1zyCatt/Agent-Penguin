import type { ReactNode, MouseEvent } from 'react';

interface ModalProps {
  open: boolean;
  title?: string;
  onClose: () => void;
  children: ReactNode;
}

const Modal = ({ open, title, onClose, children }: ModalProps) => {
  if (!open) return null;
  return (
    <div className="modal" onClick={onClose}>
      <div className="modal-card" onClick={(e: MouseEvent<HTMLDivElement>) => e.stopPropagation()}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
          <h3 style={{ margin: 0 }}>{title}</h3>
          <button className="button secondary" onClick={onClose}>
            关闭
          </button>
        </div>
        {children}
      </div>
    </div>
  );
};

export default Modal;
