declare module 'viewerjs' {
  export interface ViewerToolbarOptions {
    zoomIn?: boolean;
    zoomOut?: boolean;
    oneToOne?: boolean;
    reset?: boolean;
    prev?: boolean;
    next?: boolean;
    rotateLeft?: boolean;
    rotateRight?: boolean;
    flipHorizontal?: boolean;
    flipVertical?: boolean;
  }

  export interface ViewerOptions {
    inline?: boolean;
    navbar?: boolean;
    title?: boolean;
    toolbar?: ViewerToolbarOptions | boolean;
  }

  export default class Viewer {
    constructor(element: HTMLElement, options?: ViewerOptions);
    destroy(): void;
  }
}
