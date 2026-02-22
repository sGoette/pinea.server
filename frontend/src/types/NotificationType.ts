export enum NotificationType {
    LIBRARIES_UPDATED = 'LIBRARIES_UPDATED',
    COLLECTIONS_UPDATED = 'COLLECTIONS_UPDATED',
    MOVIES_UPDATED = 'MOVIES_UPDATED',
    NONE = 'NONE'
}

export type Notification = {
    type: NotificationType
}